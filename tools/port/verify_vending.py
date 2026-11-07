"""Continuous Vending games/replays, including authored digit and selection quirks."""
import json
from pathlib import Path
from extras_source import ExtrasSource
from export_round import Assets,activation_rows,nav_origin
from extras_vending import DEFINITIONS

def verify(source=Path('disc/2EDVD108'),analysis=Path('analysis'),output=Path('app/public')):
    data=json.loads((analysis/'extras/gateway.json').read_text());d=data['vending'];pages={p['id']:p for p in data['pages']};prov=json.loads((analysis/'extras/vending-provenance.json').read_text());mapping={};products={}
    for n,definition in enumerate(DEFINITIONS):
        intro,selector,success,wrong,pgcs,limit=definition;r=d['rounds'][n]
        for cell,id in enumerate(r['intro'],1):mapping[(intro,cell)]=id
        mapping[success,1]=r['successPage'];mapping[wrong,1]=r['wrongPage']
        for p in r['products']:
            pgc=prov[p['id']]['pgc'];products[pgc]=(n,p['id'])
            for cell,id in enumerate(p['pages'],1):mapping[pgc,cell]=id
    mapping[35,1]=d['completePage'];mapping[2,1]='vending-menu';traces=[]
    with ExtrasSource(source,analysis) as m:
        assets=Assets(source,analysis,output,m.pgcs)
        for randomized,seed in [(True,12)]+[(False,s) for s in [0,1,2,4,12,16384,30000]]:
            for strategy in ['correct','first-wrong','late-wrong','restart','recover','focus']:
                r=[0]*16;r[0]=10000 if randomized else 47;r[1]=10000;r[9]=65535;r[10]=seed;r[12]=3
                row=m.start(13,1,r);round=0;product=None;active=False;quirk=False;recovering=False
                def expected(row):
                    nonlocal round,product
                    if row['stopped'] or row['vts']!=13:raise ValueError('Unexpected Vending stop/exit')
                    if row['pgc'] in products:round,product=products[row['pgc']]
                    for n,definition in enumerate(DEFINITIONS):
                        if row['pgc']==definition[0]:round=n;product=None
                    controls=m.controls(row);ids={c['button'] for c in controls};forced={c['forcedSelect'] for c in controls if c['forcedSelect']};focus=next(iter(forced)) if forced else row['selected'];focus=focus if focus in ids else 0
                    regs=row['registers'];used=[p['id'] for p in d['rounds'][round]['products'] if regs[3]&prov[p['id']]['bit']]
                    return {'page':mapping[row['pgc'],row['cell']],'round':round,'productId':product,'order':regs[1] if active else 0,'successes':regs[4] if active else 0,'correctDigits':regs[12] if active else 0,'productCue':regs[15],'guardMarker':regs[1],'variantCue':regs[12],'selectionSeed':regs[10],'cursorCue':regs[9],'usedProducts':used if active else [],'focus':focus}
                initial=expected(row);initialDraws=[(row['registers'][15]-.5)/3] if randomized else []
                row=m.activate(row,1);active=True;steps=[{'event':{'type':'ACTIVATE','controlId':1,'time':1},'expected':expected(row),'draws':[]}]
                for _ in range(200):
                    if row['pgc']==2:break
                    page=pages[mapping[row['pgc'],row['cell']]];draws=[]
                    if row['pgc'] in products:
                        controls=page['controls'];stage=row['cell']-1;round,product=products[row['pgc']]
                        correct=[c for c in controls if c['variants'][0]['action'].get('correct')]
                        progress_wrong=[c for c in controls if c['variants'][0]['action']['type']=='vending-digit' and not c['variants'][0]['action']['correct'] and c['variants'][0]['action']['nextStage']!=stage]
                        restart=[c for c in controls if c['variants'][0]['action']['type']=='vending-digit' and c['variants'][0]['action']['nextStage']==0 and not c['variants'][0]['action']['correct']]
                        select=[c for c in controls if c['variants'][0]['action']['type']=='focus']
                        if strategy in ['restart','recover'] and restart and stage>0 and not quirk:choice=restart[0];quirk=True;recovering=strategy=='recover'
                        elif recovering and stage<round+1:choice=progress_wrong[0]
                        elif recovering:choice=correct[0];recovering=False
                        elif strategy=='focus' and select and not quirk:choice=select[0];quirk=True
                        elif strategy=='first-wrong' and row['registers'][4]==0 and row['cell']==1:choice=progress_wrong[0]
                        elif strategy=='late-wrong' and round==2 and row['registers'][1]==2 and stage==3:choice=next(c for c in progress_wrong if c['variants'][0]['action']['nextStage'] is None)
                        else:choice=correct[0]
                        source_controls=[c for c in m.controls(row) if c['button']==choice['id']];_,raw=assets.raw(m.ref(row));control,start,_=activation_rows(source_controls,nav_origin(raw))[0]
                        event={'type':'ACTIVATE','controlId':choice['id'],'time':(start+1)/90000};row=m.activate(row,control['button'],control['command'])
                    else:
                        chooses=any(row['pgc']==definition[0] and row['cell']==2 or row['pgc']==definition[2] and row['registers'][1]<2 for definition in DEFINITIONS)
                        event={'type':'SCENE_ENDED'};row=m.call('cell')
                        if randomized and chooses:draws=[(row['registers'][15]-.5)/d['rounds'][round]['randomRange']]
                    steps.append({'event':event,'expected':expected(row),'draws':draws})
                else:raise ValueError('Vending input failed to reach a result/menu')
                if strategy=='correct' and row['registers'][4]!=6:raise ValueError('Perfect Vending did not complete six orders')
                menu=expected(row);replay=[]
                row=m.activate(row,1);replay.append({'event':{'type':'ACTIVATE','controlId':1,'time':1},'expected':expected(row),'draws':[]})
                row=m.call('cell');replay.append({'event':{'type':'SCENE_ENDED'},'expected':expected(row),'draws':[]})
                row=m.call('cell');replay.append({'event':{'type':'SCENE_ENDED'},'expected':expected(row),'draws':[(row['registers'][15]-.5)/3] if randomized else []})
                traces.append({'randomized':randomized,'seed':seed,'strategy':strategy,'initial':initial,'initialDraws':initialDraws,'steps':steps,'menu':menu,'replay':replay,'quirk':quirk})
                print('Continuous source Vending',randomized,seed,strategy,'successes',menu['successes'],'quirk',quirk,flush=True)
    (analysis/'extras/vending-traces.json').write_text(json.dumps(traces,separators=(',',':'))+'\n');return traces
if __name__=='__main__':verify()
