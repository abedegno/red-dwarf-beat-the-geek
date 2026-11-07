"""Source-executed deterministic quiz entry metadata; accepted quiz banks stay immutable."""
import re
from export_extras import menu_ref
from export_round import activation_rows,nav_origin
from export_game import mode_menu_group

def build_quiz_entries(m,assets):
    def registers(flag=0,seed=1):
        r=[0]*16;r[0]=flag;r[1]=10000;r[10]=seed;r[14]=seed;return r
    def windows(pgc,group):
        ref=menu_ref(2,pgc);_,raw=assets.raw(ref);result=[]
        for row,start,end in activation_rows(group,nav_origin(raw)):
            state=m.start(2,pgc,registers(200 if pgc==8 else 221));state=m.activate(state,row['button'],row['command'])
            if (state['vts'],state['pgc'])!=(2,9):raise ValueError('Unexpected quiz menu destination')
            cue=state['registers'][12]
            if not 1<=cue<=4:raise ValueError('Invalid source variant cue')
            result.append({'startTicks':start,'endTicks':end,'variantCue':cue})
        return result
    rows=m.buttons.controls(menu_ref(2,8));xs={r['rectangle'][0] for r in rows}
    holly={id:windows(8,[r for r in rows if r['rectangle'][0]==x]) for id,x in [('norman',min(xs)),('hattie',max(xs))]}
    rows=m.buttons.controls(menu_ref(2,7))
    second={mode:windows(7,mode_menu_group(rows,mode)) for mode in ['viewer','geek','general-knowledge']}
    rows=m.buttons.controls(menu_ref(2,1));seeds={int(re.search(r'g\[10\] = 0x([0-9a-f]+)',m.ifo['decodedCommands'][r['command']])[1],16) for r in rows}
    setups={}
    for seed in sorted(seeds):
        setups[str(seed)]={}
        for presenter,flag in [('norman',201),('hattie',202),('two',2221)]:
            row=m.start(2,9,registers(flag,seed));refs=[]
            for _ in range(8):
                if row['vts']!=2:break
                refs.append(m.ref(row));row=m.call('cell')
            else:raise ValueError('Quiz entry did not reach quiz')
            if row['vts']!=3 or len(refs)!=3:raise ValueError('Unexpected deterministic setup sequence')
            setups[str(seed)][presenter]=[assets.register(ref) for ref in refs]
    ref=menu_ref(2,1);_,raw=assets.raw(ref);main=[]
    for control,start,end in activation_rows([r for r in rows if r['button']==1],nav_origin(raw)):
        values=registers();values[14]=0
        row=m.start(2,1,values);row=m.activate(row,1,control['command'])
        if (row['vts'],row['pgc'])!=(2,6):raise ValueError('Unexpected one-player menu entry')
        main.append({'startTicks':start,'endTicks':end,'selectionSeed':row['registers'][10]})
    return {'mainOne':main,'holly':holly,'secondMode':second,'setups':setups}
