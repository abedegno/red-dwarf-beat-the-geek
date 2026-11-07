"""Export only the additional authored two-player presentation and controls."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from two_player import TwoPlayerSource,MODES
from export_round import Assets,source_ref,control_groups,activation_rows,nav_origin
from export_game import mode_menu_group
from source_commands import validate_inventory
from mode_profiles import mode_profile

def publish_two_player(result,output):
    catalog=json.loads((output/'catalog.json').read_text())
    if catalog['sourceFingerprint']!=result['sourceFingerprint']:raise ValueError('Catalog identifies another source')
    if result.get('schemaVersion')!=1 or len(result.get('levels',[]))!=8 or len(result.get('setupOptions',[]))!=6:raise ValueError('Incomplete two-player dataset')
    for scene in result['scenes']:
        if not scene['src'].startswith('/media/') or not (output/scene['src'].lstrip('/')).is_file():raise ValueError('Missing two-player media')
    payload=(json.dumps(result,separators=(',',':'))+'\n').encode()
    name='two-player-'+hashlib.sha256(payload).hexdigest()+'.json'
    (output/'games').mkdir(exist_ok=True)
    immutable=output/'games'/name
    if immutable.exists():
        if immutable.read_bytes()!=payload:raise ValueError('Immutable two-player dataset mismatch')
    else:
        pending=immutable.with_suffix('.tmp.json');pending.write_bytes(payload);pending.replace(immutable)
    temporary=output/'two-player.tmp.json';temporary.write_bytes(payload);temporary.replace(output/'two-player.json')
    catalog['twoPlayer']={'dataPath':'/games/'+name}
    temporary=output/'catalog.tmp.json';temporary.write_text(json.dumps(catalog,separators=(',',':'))+'\n');temporary.replace(output/'catalog.json')

def export_two_player(source,analysis,output):
    with TwoPlayerSource(source,analysis) as m:
        validate_inventory(m.ifo)
        assets=Assets(source,analysis,output,m.pgcs)
        def scenes(refs):return [assets.register(r) for r in refs]
        def control(ref,rows,id,label,candidates=False):
            a=[min(r['rectangle'][0] for r in rows),min(r['rectangle'][1] for r in rows),max(r['rectangle'][2] for r in rows),max(r['rectangle'][3] for r in rows)]
            _,raw=assets.raw(ref);windows=[]
            for row,start,end in activation_rows(rows,nav_origin(raw)):
                window={'startTicks':start,'endTicks':end}
                if candidates:
                    match=re.search(r'g\[10\] = 0x([0-9a-f]+)',m.ifo['decodedCommands'][row['command']])
                    if not match:raise ValueError('Missing menu candidate')
                    window['candidateMask']=int(match[1],16)
                windows.append(window)
            return {'label':label,'rect':{'x':a[0],'y':a[1],'width':a[2]-a[0]+1,'height':a[3]-a[1]+1},'highlightSrc':assets.highlight(ref,min(rows,key=lambda r:r['button']),id),'windows':windows}
        def presentation(p):
            result={k:v for k,v in p.items() if k not in ['refs','gate']};result['scenes']=scenes(p['refs'])
            if p.get('gate'):
                g=p['gate'];r=g['ref'];id=f'two-continue-{r["vts"]}-{r["pgc"]}-{r["cell"]}'
                result['gate']={'scene':assets.register(r),'control':control(r,g['controlRows'],id,'Continue'),'loop':g['loop'],'afterScenes':scenes(g['afterRefs'])}
            return result
        ref={'vts':2,'domain':'vts-menu','pgc':1,'cell':1,'audio':0}
        rows=m.buttons.controls(ref);group=next(g for g in control_groups(rows) if {r['button'] for r in g}==set(range(5,9)))
        main={**control(ref,group,'two-main-menu','Two players',True),'scene':assets.register(ref,'question-loop'),'id':'two-players'}
        menus=[]
        for pgc in [6,7]:
            ref={**ref,'pgc':pgc};rows=m.buttons.controls(ref)
            menus.append({mode:{**control(ref,mode_menu_group(rows,mode),f'two-mode-{pgc}-{mode}',mode_profile(mode).label,True),'scene':assets.register(ref,'question-loop'),'id':f'player-{pgc-5}-{mode}'} for mode in MODES})
        setups={}
        seeds=[1,42,1234,50000,200000,1000000]+[(i*2654435761)%2147483647 for i in range(1,129)]
        for seed in seeds:
            row=m.start2(2,9,seed=seed)
            refs,_,_=m.walk(row,lambda r:r['vts']!=2)
            setups[tuple(r['pgc'] for r in refs)]=scenes(refs)
            if len(setups)==6:break
        if len(setups)!=6:raise ValueError('Incomplete two-player setup alternatives')
        levels=[]
        for vts,definition in m.levels.items():
            intros={};closings={};turns=[];cards=[]
            for bit in range(16):
                mask=1<<bit
                row=m.start2(vts,definition['introPgc'],mask=mask,remaining=13)
                refs,_,_=m.walk(row,lambda r:r['remaining']!=13)
                intros[str(mask)]=scenes(refs)
                row=m.start2(vts,definition['endingPgc'],mask=mask,remaining=0)
                refs,_,_=m.walk(row,lambda r:r['pgc']==(193 if vts==3 else 77))
                closings[str(mask)]=scenes(refs)
            for player in [0,1]:
                row=m.start2(vts,108 if vts==3 else 30,remaining=12-player)
                turns.append([assets.register(source_ref(row))])
                table={}
                for score in range(7):
                    for prior in range(6*(vts-3)+1):
                        total=prior+score
                        table[f'{score}:{total}']=presentation(m.scorecard(vts,player,score,total))
                cards.append(table)
            levels.append({'intros':intros,'closings':closings,'turns':turns,'scorecards':cards})
            print('Two-player level',vts-2,'scorecards',sum(map(len,cards)),flush=True)
        bonuses=[]
        for player in [0,1]:
            modes={}
            for mode in MODES:
                modes[mode]=[]
                for variant in [2,3]:
                    p=m.bonus_paths(mode,player,variant)
                    modes[mode].append({'introScenes':scenes(p['introRefs']),'correctChoice':p['correctChoice'],'correct':presentation(p['correct']),'wrong':presentation(p['wrong'])})
            bonuses.append(modes)
        result={'schemaVersion':1,'sourceFingerprint':m.ifo['sourceFingerprint'],'main':main,'menus':menus,'setupOptions':[setups[k] for k in sorted(setups)],'levels':levels,'bonuses':bonuses,'scenes':list(assets.scenes.values())}
        (analysis/'two-player/source-provenance.json').write_text(json.dumps(assets.provenance,indent=2)+'\n')
        print('Encoding/probing',len(assets.jobs),'two-player scenes',flush=True)
        with ThreadPoolExecutor(max_workers=assets.workers) as pool:list(pool.map(assets.encode,assets.jobs.items()))
        for scene in assets.scenes.values():
            info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output/scene['src'].lstrip('/'))]))
            video=next(s for s in info['streams'] if s['codec_type']=='video')
            if (video['width'],video['height'])!=(768,576) or abs(float(info['format']['duration'])-scene['durationSeconds'])>.12:raise ValueError('Two-player media mismatch: '+scene['id'])
        publish_two_player(result,output)
        return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('disc/2EDVD108'))
    p.add_argument('--analysis',type=Path,default=Path('analysis'))
    p.add_argument('--output',type=Path,default=Path('app/public'))
    a=p.parse_args();export_two_player(a.source.resolve(),a.analysis.resolve(),a.output.resolve())
