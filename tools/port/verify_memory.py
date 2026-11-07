"""Continuous Memory Morph source sequences, threshold scores, replay and Quit guards."""
import json
from pathlib import Path
from extras_source import ExtrasSource
from export_round import Assets,activation_rows,nav_origin
from extras_memory import RECALLS

def verify(source=Path('disc/2EDVD108'),analysis=Path('analysis'),output=Path('app/public')):
    data=json.loads((analysis/'extras/gateway.json').read_text());d=data['memory'];traces=[];result_pages={}
    for n,r in enumerate(d['rounds']):
        for id in set(r['results']):result_pages[int(id.split('-')[-1])]=(n,id)
    questions={pgc:(stage,index) for stage,ps in enumerate(RECALLS) for index,pgc in enumerate(ps)}
    with ExtrasSource(source,analysis) as m:
        assets=Assets(source,analysis,output,m.pgcs)
        for randomized,variant,seed in [(True,0,42),(True,3,200000),(False,0,42),(False,3,42)]:
            for strategy in ['perfect','threshold','fail-first','fail-second','fail-final']:
                r=[0]*16;r[0]=10000 if randomized else 47;r[1]=10000;r[9]=9000;r[10]=12;r[12]=variant
                row=m.start(14,1,r,seed=seed);stage=0;shown=[];recalled=[];phase='menu'
                def expected(row):
                    nonlocal stage,shown,recalled,phase
                    if row['vts']!=14 or row['stopped']:raise ValueError('Unexpected Memory stop/exit')
                    pgc=row['pgc']
                    if pgc in [39,40,41]:stage=pgc-39;phase='intro';shown=[];recalled=[];page=d['rounds'][stage]['intro']
                    elif 5<=pgc<=34:phase='show';shown=[*shown,pgc-4];page=d['objects'][pgc-5]['page']
                    elif pgc in questions:stage,index=questions[pgc];phase='recall';page=d['rounds'][stage]['recall'][index]
                    elif pgc in result_pages:stage,page=result_pages[pgc];phase='result'
                    elif pgc==36:phase='menu';page='memory-menu'
                    else:raise ValueError('Unknown Memory source page')
                    controls=m.controls(row);ids={c['button'] for c in controls};forced={c['forcedSelect'] for c in controls if c['forcedSelect']};focus=next(iter(forced)) if forced else row['selected'];focus=focus if focus in ids else 0
                    regs=row['registers']
                    return {'page':page,'stage':stage,'phase':phase,'cue':regs[15],'shown':shown[:],'recalled':recalled[:],'score':regs[14] if phase in ['recall','result','menu'] else 0,'focus':focus,'guardMarker':regs[1],'cursorCue':regs[9],'selectionSeed':regs[10],'variantCue':regs[12]}
                initial=expected(row);initialDraws=[(row['registers'][15]-.5)/30] if randomized else []
                row=m.activate(row,1);steps=[{'event':{'type':'ACTIVATE','controlId':1,'time':1},'expected':expected(row),'draws':[]}]
                for _ in range(160):
                    if row['pgc']==36:break
                    draws=[];pgc=row['pgc']
                    if pgc in questions:
                        stage,index=questions[pgc];length=d['rounds'][stage]['length'];correct=row['registers'][index+1]//1000
                        if strategy=='threshold':right=index<([3,5,7][stage])
                        else:right=not(strategy=='fail-first' and stage==0 or strategy=='fail-second' and stage==1 or strategy=='fail-final' and stage==2)
                        object=correct if right else correct%30+1
                        controls=[c for c in m.controls(row) if c['button']==object];_,raw=assets.raw(m.ref(row));control,start,_=activation_rows(controls,nav_origin(raw))[0]
                        recalled.append(object);event={'type':'ACTIVATE','controlId':object,'time':(start+1)/90000};row=m.activate(row,object,control['command'])
                    else:
                        chooses=5<=pgc<=34 or pgc in [40,41]
                        event={'type':'SCENE_ENDED'};row=m.call('cell')
                        if randomized and chooses:draws=[(row['registers'][15]-.5)/30]
                    steps.append({'event':event,'expected':expected(row),'draws':draws})
                else:raise ValueError('Memory game did not reach a menu')
                menu=steps[-1]['expected'];m.call('save 400');replay=[]
                row=m.activate(row,1);replay.append({'event':{'type':'ACTIVATE','controlId':1,'time':1},'expected':expected(row),'draws':[]})
                row=m.call('cell');replay.append({'event':{'type':'SCENE_ENDED'},'expected':expected(row),'draws':[]})
                row=m.call('restore 400');row=m.activate(row,3)
                if (row['vts'],row['domain'],row['pgc'])==(0,4,3):quit='restart'
                elif (row['vts'],row['domain'],row['pgc'])==(2,8,4):quit='archive-intro'
                else:raise ValueError('Unexpected Memory Quit route')
                traces.append({'randomized':randomized,'variant':variant,'seed':seed,'strategy':strategy,'initial':initial,'initialDraws':initialDraws,'steps':steps,'menu':menu,'replay':replay,'quit':quit})
                print('Continuous source Memory',randomized,variant,strategy,'stage',menu['stage'],'score',menu['score'],'quit',quit,flush=True)
    (analysis/'extras/memory-traces.json').write_text(json.dumps(traces,separators=(',',':'))+'\n');return traces
if __name__=='__main__':verify()
