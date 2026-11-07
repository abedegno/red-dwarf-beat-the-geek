"""Verify continuous offline source games against exported native feedback/scorecards.

Run from the repository root after export_game.py. This read-only verifier writes
local evidence under analysis/progression; it never enters the browser runtime.
The late-timeouts run answers early untimed questions wrong, then leaves every
later question unanswered. Source execution is continuous across all48 questions.
"""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from progression_model import SourceModel
from export_round import source_ref,Assets,activation_rows,choice_groups
from mode_profiles import mode_profile
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--mode',default='general-knowledge')
parser.add_argument('--presenter',default='norman')
args=parser.parse_args();profile=mode_profile(args.mode,args.presenter)
source=Path('disc/2EDVD108');analysis=Path('analysis')
data=json.loads((Path('app/public')/profile.dataset_file).read_text())
results=[]
with SourceModel(source,analysis,profile) as m:
 assets=Assets(source,analysis,Path('app/public'),m.pgcs)
 for mode in ['correct','wrong','mixed','late-timeouts']:
  row=m.start(3,m.levels[3]['introPgc'],mask=1,remaining=7,seed=42)
  events=[];n=0;bonus=False;expected=0
  for step in range(2500):
   ref=source_ref(row)
   if row['vts']==2:break
   scene=assets.register(ref)
   assert scene in {s['id'] for s in data['scenes']},(mode,n,ref,events[-4:])
   level=row['vts']-2
   if row['domain']==2:
    assert row['cell']==expected+1,(mode,ref,expected)
    round_score=6 if mode=='correct' else 3 if mode=='mixed' else 0
    ending=data['levels'][level-1]['endings'][f'{round_score}:{expected}:{row["candidate"]}']
    assert scene in ending['scenes'],(mode,level,scene,ending)
    events.append({'event':'scorecard','level':level,'total':expected,'audio':row['audio'],'scene':scene})
   if m.is_question(row):
    q=next(q for q in data['levels'][level-1]['questions'] if int(q['id'].split('-')[-1])==row['pgc'])
    correct=mode=='correct' or mode=='mixed' and n%2==0
    remaining=row['remaining'];variant=row['variant'];slot=row['registers'][11]
    if mode=='late-timeouts' and level>=4:
     initial=row;loops=0
     while row['pgc']==initial['pgc'] and row['cell']==initial['cell']:
      row=m.oracle.call('cell');loops+=1
      assert loops<=4,(q['id'],loops)
     expected_plays=max(1,q.get('promptPlays',1)-initial['registers'][9])
     assert loops==expected_plays,(q['id'],loops,expected_plays,initial['registers'][9])
    else:
     ids=q['correctSequence'] if q['kind']=='sequence' and correct else ['A']*4 if q['kind']=='sequence' else [q['correctChoice'] if correct else next(c['id'] for c in q['choices'] if c['id']!=q['correctChoice'])]
     controls=m.buttons.controls(ref)
     for choice in ids:
      group=choice_groups(controls)['ABCD'.index(choice)]
      button=activation_rows(group,min(r['vobuStart'] for r in controls))[0][0]
      m.oracle.call('select '+str(button['button']))
      row=m.oracle.call('answer '+button['command'])
     expected+=int(correct)
     w=next(w for w in q['windows'] if w['choiceId']==ids[-1])
     candidate=w['nextCandidateMask'] or slot
     key=f"{variant}:{slot}:{'correct' if correct else 'wrong'}:{candidate}:{w['feedbackVariant']}"
     refs,row,_=m.walk(row,lambda r:r['remaining']!=remaining)
     actual=[assets.register(r) for r in refs]
     assert actual==data['levels'][level-1]['answers'][key],(mode,n,q['id'],key,actual,data['levels'][level-1]['answers'][key])
    n+=1;events.append({'event':'answer','number':n,'question':q['id'],'total':expected})
    assert row['registers'][1]%100==expected,(mode,n,row['registers'][1],expected)
    continue
   if row['vts']==10 and row['pgc'] in profile.bonus_pgcs and row['cell']==2:
    bonus=True;b=next(b for b in data['bonuses'] if b['question']['id']==('perfect-bonus-low' if row['pgc']==profile.bonus_pgcs[0] else 'perfect-bonus-high'))
    controls=m.buttons.controls(ref);top=b['question']['choices']['ABCD'.index(b['question']['correctChoice'])]['rect']['y']
    button=min((r for r in controls if r['rectangle'][1]==top),key=lambda r:r['button'])
    row=m.oracle.call('answer '+button['command']);continue
   controls=m.buttons.controls(ref) if row['domain']==8 else []
   if controls:
    assert len({r['command'] for r in controls})==1,ref
    row=m.oracle.call('answer '+controls[0]['command'])
   else:row=m.oracle.call('cell')
  else:raise AssertionError('continuous source failed to terminate')
  assert n==48,(mode,n)
  assert expected=={'correct':48,'wrong':0,'mixed':24,'late-timeouts':0}[mode],(mode,expected)
  assert bonus==(mode=='correct')
  results.append({'mode':mode,'total':expected,'bonus':bonus,'events':events})
  print(mode,n,expected,bonus,flush=True)
target=Path('analysis/progression/continuous-source.json') if profile.id=='general-knowledge' else Path('analysis/modes')/profile.id/'continuous-source.json'
if profile.presenter!='norman':target=target.with_name('continuous-source-'+profile.presenter+'.json')
target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(results,indent=2)+'\n')
