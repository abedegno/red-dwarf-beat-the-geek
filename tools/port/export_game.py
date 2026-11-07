"""Export the supported complete game as native semantic data and static assets."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess
from export_round import Assets, export_round, normalize_question, activation_rows, nav_origin, control_groups
from progression_model import SourceModel, build_game_model
from mode_profiles import mode_profile


def mode_menu_group(rows,mode):
    groups=control_groups(rows)
    if len(groups)!=3:raise ValueError('Expected three source quiz-mode areas')
    index={'viewer':0,'geek':1,'general-knowledge':2}[mode_profile(mode).id]
    return groups[index]


def presenter_menu_group(rows,presenter):
    if presenter not in ['norman','hattie']:raise ValueError('Unsupported presenter')
    groups=control_groups(rows)
    if len(groups)!=2:raise ValueError('Expected two original Holly regions')
    groups=sorted(groups,key=lambda g:min(r['rectangle'][0] for r in g))
    return groups[0 if presenter=='norman' else 1]


def highlight_id(mode,id):
    profile=mode_profile(mode)
    return (id if profile.id=='general-knowledge' else profile.prefix+'-'+id) if profile.presenter=='norman' else 'hattie-'+profile.prefix+'-'+id


def presentation_repeat_offset(p):
    values={r['audio'] for r in p['refs'] if r['domain']=='title'}
    if len(values)!=1:raise ValueError('Ambiguous source scorecard repeat carry')
    return values.pop()


def verified_labels(labels:dict,id:str,source_sha256:str):
    entry=labels.get(id,{})
    if entry.get('verified') is not True or entry.get('sourceSha256')!=source_sha256:
        raise ValueError('Missing/unverified source caption: '+id)
    if not entry.get('text','').strip() or len(entry.get('choices',[]))!=4 or any(not x.strip() for x in entry['choices']):
        raise ValueError('Incomplete source caption: '+id)
    return entry['text'],entry['choices']


def validate_game(data:dict):
    if data.get('schemaVersion')!=2 or len(data.get('levels',[]))!=8:raise ValueError('Expected eight native levels')
    scenes={s['id'] for s in data['scenes']}
    if len(scenes)!=len(data['scenes']):raise ValueError('Duplicate scene ID')
    def scene(id):
        if id not in scenes:raise ValueError('Missing scene: '+str(id))
    def sequence(ids):
        for id in ids:scene(id)
    def question(q):
        if not q.get('text','').strip() or len(q.get('choices',[]))!=4 or any(not c.get('label','').strip() for c in q['choices']):
            raise ValueError('Missing question caption: '+q['id'])
        scene(q['promptScene'])
        if q.get('revealScene'):scene(q['revealScene'])
    def presentation(p):
        sequence(p['scenes'])
        if p.get('gate'):scene(p['gate']['scene']);sequence(p['gate']['afterScenes'])
    sequence(data['entry']['boot']);sequence(data['entry']['setupScenes'])
    for ids in data['entry'].get('setupOptions',[]):sequence(ids)
    for menu in data['entry']['menus']:scene(menu['scene'])
    ids=set()
    for number,level in enumerate(data['levels'],1):
        if level['number']!=number or len(level['questions'])!=38:raise ValueError('Incorrect native question pool')
        own={q['id'] for q in level['questions']}
        if len(own)!=38 or own&ids:raise ValueError('Duplicate native question ID')
        ids|=own
        for q in level['questions']:question(q)
        for options in level['selection'].values():
            for option in options:
                if option['questionId'] not in own:raise ValueError('Selection outside level pool')
                sequence(option['introScenes'])
        for seq in level['answers'].values():sequence(seq)
        for options in level['timeouts'].values():
            for option in options:sequence(option['feedback'])
        for seq in level['intros'].values():sequence(seq)
        for p in level['endings'].values():presentation(p)
    for bonus in data['bonuses']:
        question(bonus['question']);sequence(bonus['introScenes'])
        presentation(bonus['correct']);presentation(bonus['wrong'])


def publish_game(data:dict,output:Path,name='game.json'):
    validate_game(data)
    temporary=output/Path(name).with_suffix('.tmp.json');temporary.write_text(json.dumps(data,separators=(',',':'))+'\n')
    temporary.replace(output/name)


def export_game(source:Path,analysis:Path,output:Path,prepare_only=False,mode='general-knowledge',presenter=None):
    profile=mode_profile(mode,presenter)
    model=build_game_model(source,analysis,profile)
    # Preserve the independently verified level-one exporter and its entry flow.
    legacy=export_round(source,analysis,output)
    ifo=json.loads((analysis/'ifo.json').read_text())
    pgcs={(p['vts'],p['domain'],p['pgc']):p for p in ifo['pgcs']}
    assets=Assets(source,analysis,output,pgcs)
    provenance=json.loads((analysis/'native-provenance.json').read_text())
    for scene in legacy['scenes']:
        id=scene['id'];assets.scenes[id]=scene;assets.provenance[id]=provenance[id]
        assets.jobs[id]={**provenance[id],'audio':scene['audioVariant'] or 0}
    labels_path=Path(__file__).with_name(profile.labels_file)
    label_data=json.loads(labels_path.read_text()) if labels_path.exists() else {}
    if label_data and label_data['sourceFingerprint']!=ifo['sourceFingerprint']:raise ValueError('Game captions identify another source')
    labels=dict(label_data.get('questions',{}))
    if profile.presenter=='hattie':
        bonus_path=Path(__file__).with_name('hattie_bonus_labels.json')
        extra=json.loads(bonus_path.read_text()) if bonus_path.exists() else {}
        if extra and extra['sourceFingerprint']!=ifo['sourceFingerprint']:raise ValueError('Hattie captions identify another source')
        labels.update(extra.get('questions',{}).get(profile.id,{}))
    def scene_list(refs):return [assets.register(ref) for ref in refs]
    def captions(id,raw):
        if prepare_only:return labels.get(id,{}).get('text',id),labels.get(id,{}).get('choices',list('ABCD'))
        return verified_labels(labels,id,hashlib.sha256(raw).hexdigest())
    control_cache={}
    def timed_control(ref,rows,id):
        key=(ref['vts'],ref['pgc'],ref['cell'])
        if key in control_cache:return control_cache[key]
        if not rows or len({tuple(row['rectangle']) for row in rows})!=1:raise ValueError('Ambiguous continue geometry')
        row=min(rows,key=lambda r:r['button']);area=row['rectangle'];_,raw=assets.raw(ref)
        result={'label':'Continue','rect':{'x':area[0],'y':area[1],'width':area[2]-area[0]+1,'height':area[3]-area[1]+1},
                'highlightSrc':assets.highlight(ref,row,id),
                'windows':[{'startTicks':start,'endTicks':end} for _,start,end in activation_rows(rows,nav_origin(raw))]}
        control_cache[key]=result
        return result
    def presentation(p):
        result={'scenes':scene_list(p['refs']),'destination':p['destination'],'nextCandidateMask':p['nextCandidateMask']}
        if profile.presenter=='hattie' and p['destination']=='next-level':result['nextOrderingRepeatOffset']=presentation_repeat_offset(p)
        if p.get('gate'):
            gate=p['gate'];ref=gate['ref'];id=f'continue-{ref["vts"]}-{ref["pgc"]}-{ref["cell"]}'
            result['gate']={'scene':assets.register(ref),'control':timed_control(ref,gate['controlRows'],id),
                            'loop':gate['loop'],'afterScenes':scene_list(gate['afterRefs'])}
        return result
    levels=[]
    with SourceModel(source,analysis,profile) as source_model:
        for level in model['levels']:
            vts=level['vts'];questions=[]
            for pgc in level['questionPgcs']:
                p=pgcs[(vts,'vts-menu',pgc)];layout=source_model.question_layout(vts,pgc)
                ref={'vts':vts,'domain':'vts-menu','pgc':pgc,'cell':layout['prompt'],'audio':0}
                rows=source_model.buttons.controls(ref);_,raw=assets.raw(ref)
                q=normalize_question(p,rows,ifo['decodedCommands'],nav_origin(raw),layout['prompt'],layout['reveal']);q['id']=f'{profile.prefix}-l{level["number"]}-{pgc:03d}'
                q['text'],choices=captions(q['id'],raw)
                q.update({'expiry':level['expiry'][str(pgc)]['kind'],'promptPlays':level['expiry'][str(pgc)]['plays'],'promptScene':assets.register(ref,'question-loop'),'revealScene':assets.register({**ref,'cell':layout['reveal']})})
                for c,label in zip(q['choices'],choices):
                    c['label']=label;row=min((row for row in rows if row['rectangle'][0]>=c['rect']['x'] and row['rectangle'][1]>=c['rect']['y'] and row['rectangle'][2]<c['rect']['x']+c['rect']['width'] and row['rectangle'][3]<c['rect']['y']+c['rect']['height']),key=lambda r:r['button'])
                    c['highlightSrc']=assets.highlight(ref,row,q['id']+'-'+c['id'])
                questions.append(q)
            levels.append({'number':level['number'],'questions':questions,
                           'selection':{key:[{'questionId':o['questionId'],'introScenes':scene_list(o['introRefs']),'variant':o['variant']} for o in options] for key,options in level['routes'].items()},
                           'answers':{key:scene_list(refs) for key,refs in level['answers'].items()},
                           'timeouts':{key:[{'feedback':scene_list(o['refs']),'nextCandidateMask':o['nextCandidateMask']} for o in options] for key,options in level['timeouts'].items()},
                           'intros':{key:scene_list(refs) for key,refs in level['intros'].items()},
                           'endings':{key:presentation(p) for key,p in level['endings'].items()}})
            print('Prepared level',level['number'],'questions',len(questions),flush=True)
        bonuses=[]
        for bonus in model['bonuses']:
            ref=bonus['questionRef'];p,c=assets.parts(ref);_,raw=assets.raw(ref);text,labels_=captions(bonus['id'],raw)
            choices=[];windows=[]
            for i,row in enumerate(bonus['buttonRows']):
                a=row['rectangle'];id='ABCD'[i]
                choices.append({'id':id,'label':labels_[i],'rect':{'x':a[0],'y':a[1],'width':a[2]-a[0]+1,'height':a[3]-a[1]+1},'highlightSrc':assets.highlight(ref,row,highlight_id(profile,bonus['id']+'-'+id))})
                for _,start,end in activation_rows([r for r in bonus['controlRows'] if r['rectangle'][1]==a[1]],nav_origin(raw)):
                    windows.append({'startTicks':start,'endTicks':end,'choiceId':id,'nextCandidateMask':0})
            question={'id':bonus['id'],'text':text,'kind':'single','expiry':'timeout','choices':choices,
                      'correctChoice':bonus['correctChoice'],'correctSequence':[],'promptScene':assets.register(ref),
                      'revealScene':None,'durationSeconds':c['duration'],'revealSeconds':0,'windows':windows}
            bonuses.append({'id':bonus['id'],'introScenes':scene_list(bonus['introRefs']),'question':question,'correct':presentation(bonus['correct']),'wrong':presentation(bonus['wrong'])})
    setup_options=None;holly_menu=None
    if profile.presenter=='hattie':
        with SourceModel(source,analysis,profile) as source_model:
            setup_options=[scene_list(refs) for refs in source_model.entry_setups()]
            ref={'vts':2,'domain':'vts-menu','pgc':8,'cell':1,'audio':0}
            rows=source_model.buttons.controls(ref)
        group=presenter_menu_group(rows,'hattie');row=min(group,key=lambda r:r['button'])
        a=[min(r['rectangle'][0] for r in group),min(r['rectangle'][1] for r in group),max(r['rectangle'][2] for r in group),max(r['rectangle'][3] for r in group)]
        _,raw=assets.raw(ref)
        holly_menu={'id':'holly','scene':assets.register(ref,'question-loop'),'label':'Hattie Hayridge’s Holly',
          'rect':{'x':a[0],'y':a[1],'width':a[2]-a[0]+1,'height':a[3]-a[1]+1},
          'highlightSrc':assets.highlight(ref,row,'menu-hattie-holly'),
          'windows':[{'startTicks':start,'endTicks':end,'candidateMask':int(re.search(r'g\[10\] = 0x([0-9a-f]+)',ifo['decodedCommands'][control['command']])[1],16)} for control,start,end in activation_rows(group,nav_origin(raw))]}
    print('Encoding/probing',len(assets.jobs),'distinct source scenes',flush=True)
    with ThreadPoolExecutor(max_workers=assets.workers) as pool:list(pool.map(assets.encode,assets.jobs.items()))
    for scene in assets.scenes.values():
        info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output/scene['src'].lstrip('/'))]))
        video=next(s for s in info['streams'] if s['codec_type']=='video')
        if (video['width'],video['height'])!=(768,576) or abs(float(info['format']['duration'])-scene['durationSeconds'])>.12:raise ValueError('Prepared game scene mismatch: '+scene['id'])
        if any(s['codec_type']=='audio' for s in info['streams'])!=(scene['audioVariant'] is not None):raise ValueError('Prepared game audio mismatch: '+scene['id'])
    entry={k:v for k,v in legacy['entry'].items() if k!='roundIntros'}
    if profile.id!='general-knowledge':
        ref={'vts':2,'domain':'vts-menu','pgc':6,'cell':1,'audio':0}
        with SourceModel(source,analysis,profile) as source_model:rows=source_model.buttons.controls(ref)
        group=mode_menu_group(rows,profile);row=min(group,key=lambda r:r['button'])
        area=[min(r['rectangle'][0] for r in group),min(r['rectangle'][1] for r in group),
              max(r['rectangle'][2] for r in group),max(r['rectangle'][3] for r in group)]
        _,raw=assets.raw(ref)
        windows=[]
        for control,start,end in activation_rows(group,nav_origin(raw)):
            match=re.search(r'g\[10\] = 0x([0-9a-f]+)',ifo['decodedCommands'][control['command']])
            if not match:raise ValueError('Unsupported mode menu candidate')
            windows.append({'startTicks':start,'endTicks':end,'candidateMask':int(match[1],16)})
        entry['menus'][1]={'id':'player-type','scene':assets.register(ref,'question-loop'),'label':profile.label,
            'rect':{'x':area[0],'y':area[1],'width':area[2]-area[0]+1,'height':area[3]-area[1]+1},
            'highlightSrc':assets.highlight(ref,row,'menu-mode-'+profile.id),'windows':windows}
    if holly_menu:
        entry['menus'][2]=holly_menu;entry['setupScenes']=setup_options[0];entry['setupOptions']=setup_options
    result={'schemaVersion':2,'sourceFingerprint':ifo['sourceFingerprint'],'scenes':list(assets.scenes.values()),
            'entry':entry,'levels':levels,'bonuses':bonuses}
    if not prepare_only:publish_game(result,output,profile.dataset_file)
    (analysis/profile.provenance_file).write_text(json.dumps(assets.provenance,indent=2)+'\n')
    print('Prepared only; playable data unchanged' if prepare_only else 'Published complete semantic game',flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('disc/2EDVD108'))
    parser.add_argument('--analysis',type=Path,default=Path('analysis'))
    parser.add_argument('--output',type=Path,default=Path('app/public'))
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--mode',default='general-knowledge')
    parser.add_argument('--presenter',default='norman')
    args=parser.parse_args();export_game(args.source.resolve(),args.analysis.resolve(),args.output.resolve(),args.prepare_only,args.mode,args.presenter)
