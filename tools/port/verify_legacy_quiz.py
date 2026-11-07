"""Continuous deterministic source quiz traces from actual original menus, offline only."""
import json
from itertools import product
from pathlib import Path
from button_index import ButtonIndex
from extras_source import ExtrasSource
from export_extras import menu_ref
from export_game import mode_menu_group
from export_round import Assets,activation_rows,choice_groups,nav_origin
from mode_profiles import mode_profile

MODES=['viewer','geek','general-knowledge']
def verify(source=Path('disc/2EDVD108'),analysis=Path('analysis'),output=Path('app/public')):
    banks={(p,mode):json.loads((output/mode_profile(mode,p).dataset_file).read_text()) for p in ['norman','hattie'] for mode in MODES}
    traces=[]
    with ExtrasSource(source,analysis) as m:
        with (analysis/'buttons.jsonl').open() as f:m.__dict__['buttons']=ButtonIndex(m.ifo,(json.loads(line) for line in f))
        assets=Assets(source,analysis,output,m.pgcs)
        def pick(row,group):
            _,raw=assets.raw(m.ref(row));control,start,_=activation_rows(group,nav_origin(raw))[0]
            return m.activate(row,control['button'],control['command']),(start+1)/90000
        cases=[([mode],p) for p in ['norman','hattie'] for mode in MODES]+[(list(modes),None) for modes in product(MODES,repeat=2)]
        for modes,presenter in cases:
            r=[0]*16;r[0]=47;r[1]=10000;r[10]=1
            row=m.start(2,1,r);two=len(modes)==2
            button=5 if two else 1
            row,time=pick(row,[r for r in m.controls(row) if r['button']==button])
            events=[{'type':'CHOOSE_PLAYERS' if two else 'MENU_CHOOSE','time':time}]
            for mode in modes:
                row,time=pick(row,mode_menu_group(m.controls(row),mode));events.append({'type':'CHOOSE_MODE','modeId':mode,'time':time})
            if not two:
                controls=m.controls(row);xs=[r['rectangle'][0] for r in controls];x=min(xs) if presenter=='norman' else max(xs)
                row,time=pick(row,[r for r in controls if r['rectangle'][0]==x]);events.append({'type':'CHOOSE_PRESENTER','presenterId':presenter,'time':time})
            questions=[];setup=[]
            for _ in range(3000):
                if row['vts']==2 and row['pgc']==1:break
                n=len(questions);player=n%2 if two else 0;p=('norman' if player==0 else 'hattie') if two else presenter
                bank=banks[p,modes[player]];level=row['vts']-3
                q=next((q for q in bank['levels'][level]['questions'] if int(q['id'].split('-')[-1])==row['pgc']),None) if row['domain']==8 and 0<=level<8 else None
                if q and assets.register(m.ref(row))!=q['promptScene']:q=None
                if q:
                    record={'id':q['id'],'variant':row['registers'][12],'slot':row['registers'][11],'level':level,'player':player,'choices':[]}
                    ids=['A']*4 if q['kind']=='sequence' else [next(c['id'] for c in q['choices'] if c['id']!=q['correctChoice'])]
                    for choice in ids:
                        controls=m.controls(row)
                        if not controls:raise ValueError(f'Missing quiz controls case={modes}/{presenter} n={n} q={q["id"]} choice={choice} at {m.ref(row)}')
                        group=choice_groups(controls)['ABCD'.index(choice)]
                        row,time=pick(row,group);record['choices'].append({'id':choice,'time':time})
                    questions.append(record);continue
                if not questions and row['vts']==2:setup.append(assets.register(m.ref(row)))
                controls=m.controls(row)
                if controls:
                    commands={c['command'] for c in controls}
                    if len(commands)!=1:raise ValueError(f'Unclassified source controls: {m.ref(row)}')
                    row=m.activate(row,controls[0]['button'],controls[0]['command'])
                else:row=m.call('cell')
            else:raise ValueError('Legacy source game did not finish')
            if len(questions)!=(96 if two else 48):raise ValueError(f'Wrong source question count {len(questions)}')
            traces.append({'modes':modes,'presenter':presenter,'events':events,'setup':setup,'questions':questions})
            print('Legacy source',modes,presenter,len(questions),'questions',flush=True)
    (analysis/'extras/legacy-quiz-traces.json').write_text(json.dumps(traces,separators=(',',':'))+'\n')
    return traces
if __name__=='__main__':verify()
