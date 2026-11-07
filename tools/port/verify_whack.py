"""Continuous original Whack games, including the terminal cursor selector and replay."""
import json
from pathlib import Path
from extras_source import ExtrasSource
from export_round import Assets,activation_rows,nav_origin

def verify(source=Path('disc/2EDVD108'),analysis=Path('analysis'),output=Path('app/public')):
    data=json.loads((analysis/'extras/gateway.json').read_text());whack=data['whack'];traces=[]
    with ExtrasSource(source,analysis) as m:
        assets=Assets(source,analysis,output,m.pgcs)
        def expected(row):
            r=row['registers'];terminal=row['pgc']==25
            return {'page':whack['results'][r[5]] if terminal else whack['positions'][r[6]-1], 'attempt':r[7],'score':r[5],'positionSeed':r[6],'cursorStep':r[8],'cursorCue':r[9],'selectionSeed':r[10],'focus':0 if terminal else row['selected'] if 1<=row['selected']<=9 else 0,'terminal':terminal}
        for randomized in [True,False]:
            for strategy in ['correct','wrong','mixed','expiry']:
                r=[0]*16;r[0]=10000 if randomized else 47;r[1]=10000;r[10]=1;r[9]=9000
                row=m.start(12,1,r);row=m.activate(row,1);initial=expected(row);steps=[]
                for n in range(20):
                    controls=m.controls(row);correct=[c for c in controls if 'LinkPGCN 5' in m.ifo['decodedCommands'][c['command']]];wrong=[c for c in controls if 'LinkPGCN 6' in m.ifo['decodedCommands'][c['command']]]
                    hit=strategy!='expiry' and (strategy=='wrong' or strategy=='mixed' and n%2==1 or bool(correct))
                    if hit:
                        choice=wrong[0] if strategy=='wrong' or strategy=='mixed' and n%2==1 else correct[0]
                        _,raw=assets.raw(m.ref(row));control,start,_=activation_rows([c for c in controls if c['button']==choice['button']],nav_origin(raw))[0]
                        event={'type':'ACTIVATE','controlId':control['button'],'time':(start+1)/90000};row=m.activate(row,control['button'],control['command'])
                    else:event={'type':'SCENE_ENDED'};row=m.call('cell')
                    steps.append({'event':event,'expected':expected(row)})
                if row['pgc']!=25 or row['registers'][7]!=20:raise ValueError('Whack failed to stop after20 appearances')
                row=m.call('cell')
                if row['pgc']!=7:raise ValueError('Whack result failed to return')
                menu={'cursorStep':row['registers'][8],'cursorCue':row['registers'][9],'selectionSeed':row['registers'][10]}
                row=m.activate(row,1);replay=expected(row)
                traces.append({'randomized':randomized,'strategy':strategy,'initialCursor':9000,'initial':initial,'steps':steps,'menu':menu,'replay':replay})
                print('Continuous source Whack',randomized,strategy,'score',steps[-1]['expected']['score'],flush=True)
    (analysis/'extras/whack-traces.json').write_text(json.dumps(traces,separators=(',',':'))+'\n');return traces
if __name__=='__main__':verify()
