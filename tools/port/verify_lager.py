"""Continuous real-source Lager success, decoy and each-stage expiry paths."""
import json
from pathlib import Path
from extras_source import ExtrasSource
from export_round import Assets,activation_rows,nav_origin

def verify(source=Path('disc/2EDVD108'),analysis=Path('analysis'),output=Path('app/public')):
 data=json.loads((analysis/'extras/gateway.json').read_text());traces=[]
 def name(row):
  p,c=row['pgc'],row['cell']
  if p==15:return 'lager-menu'
  if p in [12,13,14]:return {12:'lager-fail',13:'lager-intro',14:'lager-interlude'}[p]
  return f"lager-{['aim','hit','transition'][c-1]}-{p-1}"
 with ExtrasSource(source,analysis) as m:
  assets=Assets(source,analysis,output,m.pgcs)
  for randomized in [True,False]:
   for strategy in ['success','decoy',*range(1,11)]:
    regs=[0]*16;regs[0]=10000 if randomized else 47;regs[1]=12000;regs[9]=7000;regs[10]=4;regs[12]=3000
    row=m.start(15,1,regs);steps=[]
    def expected(row):
     controls=m.controls(row);ids={c['button'] for c in controls};r=row['registers'];return {'page':name(row),'focus':row['selected'] if row['selected'] in ids else 0,'context':{'randomized':r[0]!=47,'guardMarker':r[1],'cursorCue':r[9],'selectionSeed':r[10],'variantCue':r[12]}}
    initial=expected(row);row=m.activate(row,1);steps.append({'event':{'type':'ACTIVATE','controlId':1,'time':1},'expected':expected(row)})
    for _ in range(60):
     if row['pgc']==15:break
     if 2<=row['pgc']<=11 and row['cell']==1 and strategy!=row['pgc']-1:
      controls=m.controls(row);_,raw=assets.raw(m.ref(row));windows=activation_rows(controls,nav_origin(raw));decoy=strategy=='decoy' and row['pgc']==4
      window=next(w for w in windows if ('LinkPGCN 12'==m.ifo['decodedCommands'][w[0]['command']])==decoy)
      c,start,end=window;event={'type':'ACTIVATE','controlId':c['button'],'time':(start+end)/180000};row=m.activate(row,c['button'],c['command'])
     else:event={'type':'SCENE_ENDED'};row=m.call('cell')
     steps.append({'event':event,'expected':expected(row)})
    else:raise ValueError('Lager path did not finish')
    row=m.activate(row,3)
    if (row['vts'],row['pgc'])!=(2,4):raise ValueError('Unexpected Lager Quit')
    traces.append({'randomized':randomized,'strategy':strategy,'initial':initial,'steps':steps});print('Continuous Lager',randomized,strategy,len(steps),flush=True)
 (analysis/'extras/lager-traces.json').write_text(json.dumps(traces,separators=(',',':'))+'\n');return traces
if __name__=='__main__':verify()
