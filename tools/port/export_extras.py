"""Offline original extras presentation. Drafts never replace the accepted catalog."""
import argparse,hashlib,json,re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from extras_source import ExtrasSource
from export_round import Assets,activation_rows,nav_origin
from timed_spu import extract_timed_packets,display_intervals
import spu

GAME_ENTRIES={'maze':(11,17,17),'whack':(12,7,26),'vending':(13,2,3),'memory':(14,36,76),'lager':(15,15,16)}
CODES={'7523':'maze','1921':'whack','3598':'vending','9639':'memory','7148':'lager'}

def menu_ref(vts,pgc,cell=1):return {'vts':vts,'domain':'vts-menu','pgc':pgc,'cell':cell,'audio':0}

class ExtraAssets:
    def __init__(self,source,assets):self.source,self.assets=source,assets;self._packets={};self._bitmaps={};self._rgba={}
    def packets(self,ref):
        _,raw=self.assets.raw(ref);key=hashlib.sha256(raw).hexdigest()
        if key not in self._packets:self._packets[key]=extract_timed_packets(raw)
        return raw,self._packets[key]
    def raster(self,ref,bitmap,table,clip=None):
        p,_=self.assets.parts(ref);rect=bitmap['rect']
        key=(tuple(p['palette']),table,tuple(tuple(row) for row in bitmap['pixels']))
        if key not in self._rgba:self._rgba[key]=spu.render_rgba(bitmap['pixels'],p['palette'],table)
        rgba=self._rgba[key];out=bytearray(720*576*4)
        area=clip or [0,0,719,575]
        for y in range(max(area[1],rect['y']),min(area[3]+1,rect['y']+rect['height'])):
            left=max(area[0],rect['x']);right=min(area[2]+1,rect['x']+rect['width'])
            if right<=left:continue
            begin=((y-rect['y'])*rect['width']+left-rect['x'])*4
            out[(y*720+left)*4:(y*720+right)*4]=rgba[begin:begin+(right-left)*4]
        name='extra-'+hashlib.sha256(out).hexdigest()+'.png';target=self.assets.media/name
        spu.write_png(target,720,576,out)
        return '/media/'+name
    def highlight(self,ref,row):
        _,packets=self.packets(ref)
        applicable=[p for p in packets if p['stream']==32 and p['pts']<=row['highlightStart']]
        if not applicable:raise ValueError('No source bitmap at highlight onset')
        packet=applicable[-1]['data']
        if packet not in self._bitmaps:self._bitmaps[packet]=display_intervals(packet)
        bitmap=self._bitmaps[packet][0]
        table=row['colourTable'][row['colourIndex']-1][0]
        return self.raster(ref,bitmap,table,row['rectangle'])
    def controls(self,ref,actions):
        rows=self.source.buttons.controls(ref);raw,_=self.packets(ref);origin=nav_origin(raw)
        groups=defaultdict(list)
        for r in rows:groups[r['button']].append(r)
        result=[]
        if set(groups)!=set(actions):raise ValueError(f'Unmapped original controls at {ref}: {set(groups)^set(actions)}')
        for id,group in sorted(groups.items()):
            # These gateway/menu pages have one fixed neighbour graph per button.
            if len({json.dumps(r['neighbours'],sort_keys=True) for r in group})!=1:raise ValueError('Changing source neighbour graph')
            label,action=actions[id];variants=[]
            for row,start,end in activation_rows(group,origin):
                area=row['rectangle'];variants.append({'startTicks':start,'endTicks':end,'rect':{'x':area[0],'y':area[1],'width':area[2]-area[0]+1,'height':area[3]-area[1]+1},'highlightSrc':self.highlight(ref,row),'action':action})
            result.append({'id':id,'label':label,'neighbours':group[0]['neighbours'],'autoActivate':bool(group[0]['autoAction']),'variants':variants})
        return result
    def subtitles(self,ref):
        raw,packets=self.packets(ref);origin=nav_origin(raw);scene=self.assets.register(ref);result=[]
        for p in packets:
            if p['stream']!=32:continue
            for bitmap in display_intervals(p['data']):
                if bitmap['endTicks'] is None:raise ValueError('Instruction caption has no end')
                result.append({'scene':scene,'startTicks':p['pts']+bitmap['startTicks']-origin,'endTicks':p['pts']+bitmap['endTicks']-origin,'src':self.raster(ref,bitmap,bitmap['palette']<<16|bitmap['alpha'])})
        return result

def build_gateway(m,assets):
    extra=ExtraAssets(m,assets);pages=[]
    def page(id,ref,actions=None,after=None,focus=None):
        controls=extra.controls(ref,actions) if actions else []
        selected=focus if focus is not None else (m.start(ref['vts'],ref['pgc'])['selected'] if ref['domain']=='vts-menu' else 0)
        forced={r['forcedSelect'] for r in m.buttons.controls(ref) if r['forcedSelect']} if controls else set()
        if len(forced)>1:raise ValueError('Changing forced selection needs an explicit page rule')
        if forced:selected=forced.pop()
        if not controls or selected not in {c['id'] for c in controls}:selected=0
        pages.append({'id':id,'scene':assets.register(ref,'question-loop' if after is None else 'clip'),'loop':after is None,'focus':selected,'controls':controls,'after':after})
    page('instructions-choice',menu_ref(2,26),{1:('Play',{'type':'instructions','subtitles':False}),2:('Play With Subtitles',{'type':'instructions','subtitles':True}),3:('Main Menu',{'type':'main-menu'})})
    # The first cell command is LinkTailPGC: the short second title cell is skipped.
    instructions={'vts':2,'domain':'title','pgc':1,'cell':1,'audio':0}
    page('instructions-video',instructions,after={'type':'main-menu'})
    page('archive-intro',menu_ref(2,4),after={'type':'page','page':'keypad-0'})
    for index in range(4):
        actions={i:(str(i%10),{'type':'digit','digit':i%10}) for i in range(1,11)};actions[11]=('Menu',{'type':'main-menu'})
        page(f'keypad-{index}',menu_ref(2,24,index+1),actions,focus=11)
    page('keypad-confirm',menu_ref(2,24,5),after={'type':'dispatch-code'})
    page('invalid-code',menu_ref(2,27),after={'type':'main-menu'})
    games={}
    for id,(vts,menu,help) in GAME_ENTRIES.items():
        games[id]={'menuPage':id+'-menu','instructionPage':id+'-menu' if menu==help else id+'-help'}
        actions={1:('Play',{'type':'game','action':'play'})}
        if menu==help:actions[2]=('Quit',{'type':'archive-quit'})
        else:actions.update({2:('Instructions',{'type':'page','page':id+'-help'}),3:('Quit',{'type':'archive-quit'})})
        page(id+'-menu',menu_ref(vts,menu),actions)
        if menu!=help:
            ref=menu_ref(vts,help);rows=m.buttons.controls(ref)
            controls={r['button']:('Back',{'type':'page','page':id+'-menu'}) for r in rows}
            m.start(vts,help);after=m.call('cell')
            if after['stopped']:ending={'type':'stop'}
            elif m.ref(after)==ref:ending=None
            elif (after['vts'],after['domain'],after['pgc'])==(vts,8,menu):ending={'type':'page','page':id+'-menu'}
            else:raise ValueError('Unmapped original instruction-screen return')
            page(id+'-help',ref,controls,after=ending)
    ref=menu_ref(2,1);rows=m.buttons.controls(ref);_,raw=assets.raw(ref);origin=nav_origin(raw);main={}
    for id,button,label in [('instructions',9,'How to Play'),('archive',13,'Games Archive')]:
        group=[r for r in rows if r['button']==button];first=group[0];a=first['rectangle'];windows=[]
        for row,start,end in activation_rows(group,origin):
            text=m.ifo['decodedCommands'][row['command']];match=re.search(r'g\[10\] = 0x([0-9a-f]+)',text)
            if not match:raise ValueError('Missing main menu selection seed')
            windows.append({'startTicks':start,'endTicks':end,'selectionSeed':int(match[1],16)})
        main[id]={'label':label,'rect':{'x':a[0],'y':a[1],'width':a[2]-a[0]+1,'height':a[3]-a[1]+1},'highlightSrc':extra.highlight(ref,first),'windows':windows}
    return {'schemaVersion':1,'sourceFingerprint':m.ifo['sourceFingerprint'],'main':main,'pages':pages,'subtitles':extra.subtitles(instructions),'codes':CODES,'games':games,'scenes':list(assets.scenes.values())}

from extras_validation import validate_extras,extras_media

def publish_extras(result,output):
    catalog=json.loads((output/'catalog.json').read_text())
    validate_extras(result,output,catalog['sourceFingerprint'])
    payload=(json.dumps(result,separators=(',',':'))+'\n').encode()
    name='extras-'+hashlib.sha256(payload).hexdigest()+'.json'
    (output/'games').mkdir(exist_ok=True)
    immutable=output/'games'/name
    if immutable.exists():
        if immutable.read_bytes()!=payload:raise ValueError('Immutable extras dataset mismatch')
    else:
        pending=immutable.with_suffix('.tmp.json');pending.write_bytes(payload);pending.replace(immutable)
    catalog['extras']={'dataPath':'/games/'+name}
    pending=output/'catalog.tmp.json';pending.write_text(json.dumps(catalog,separators=(',',':'))+'\n');pending.replace(output/'catalog.json')
    return catalog

def export_gateway(source,analysis,output):
    with ExtrasSource(source,analysis) as m:
        assets=Assets(source,analysis,output,m.pgcs);result=build_gateway(m,assets)
        from extras_maze import build_maze
        from extras_quiz import build_quiz_entries
        maze=build_maze(m,assets);result['pages'].extend(maze.pop('pages'));result['maze']=maze
        result['quizEntry']=build_quiz_entries(m,assets)
        from extras_whack import build_whack
        whack=build_whack(m,assets);result['pages'].extend(whack.pop('pages'));result['whack']=whack
        from extras_vending import build_vending
        vending=build_vending(m,assets);result['pages'].extend(vending.pop('pages'));result['vending']=vending
        from extras_memory import build_memory
        memory=build_memory(m,assets);result['pages'].extend(memory.pop('pages'));result['memory']=memory
        from extras_lager import build_lager
        lager=build_lager(m,assets);result['pages'].extend(lager.pop('pages'));result['lager']=lager
        with ThreadPoolExecutor(max_workers=assets.workers) as pool:list(pool.map(assets.encode,assets.jobs.items()))
        result['scenes']=list(assets.scenes.values())
        (analysis/'extras/gateway.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
        (analysis/'extras/source-provenance.json').write_text(json.dumps(assets.provenance,indent=2)+'\n')
        print('Draft gateway:',len(result['pages']),'pages,',len(result['subtitles']),'subtitle rasters; catalog unchanged')
        return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--publish',action='store_true',help='Publish the complete verified draft atomically');p.add_argument('--source',type=Path,default=Path('disc/2EDVD108'));p.add_argument('--analysis',type=Path,default=Path('analysis'));p.add_argument('--output',type=Path,default=Path('app/public'));a=p.parse_args();result=export_gateway(a.source.resolve(),a.analysis.resolve(),a.output.resolve());publish_extras(result,a.output.resolve()) if a.publish else None
