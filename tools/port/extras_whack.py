"""Source-executed Whack-a-Flibble targets, next-position seeds and results."""
from export_extras import ExtraAssets

def build_whack(m,assets):
    extra=ExtraAssets(m,assets);pages=[];positions=[];results=[];cycle=[]
    def registers():
        r=[0]*16;r[0]=47;r[1]=10000;r[10]=1;r[8]=1;r[9]=1;return r
    for position in range(1,18):
        r=registers();r[6]=position-1;r[7]=19;r[5]=5
        row=m.start(12,4,r);ref=m.ref(row);controls=m.controls(row);groups={}
        if row['registers'][6]!=position or row['registers'][7]!=20:raise ValueError('Unexpected Whack selector')
        for c in controls:groups.setdefault(c['button'],[]).append(c)
        if set(groups)!=set(range(1,10)):raise ValueError('Missing original Whack hole')
        actions={}
        for id,group in groups.items():
            if len({c['command'] for c in group})!=1:raise ValueError('Changing Whack hotspot action')
            initial=m.start(12,4,r);after=m.activate(initial,id)
            score=after['registers'][5];seed=after['registers'][6]
            if after['pgc']!=25 or score not in [4,6] or not 0<=seed<=17:raise ValueError('Unsupported source Whack hit')
            actions[id]=(f'Hole {id}',{'type':'whack-hit','correct':score==6,'positionSeed':seed})
        id=f'whack-frame-{position}';positions.append(id)
        pages.append({'id':id,'scene':assets.register(ref),'loop':False,'focus':0,'controls':extra.controls(ref,actions),'after':{'type':'whack-next'}})
    for score in range(21):
        r=registers();r[5]=score;r[7]=20;row=m.start(12,25,r);ref=m.ref(row)
        if row['cell']!=score+1 or m.controls(row):raise ValueError('Unsupported Whack result layout')
        after=m.call('cell')
        if (after['vts'],after['pgc'])!=(12,7):raise ValueError('Whack result does not return to menu')
        id=f'whack-score-{score}';results.append(id)
        pages.append({'id':id,'scene':assets.register(ref),'loop':False,'focus':0,'controls':[],'after':{'type':'whack-menu'}})
    for step in range(1,18):
        r=registers();r[8]=step;r[7]=20;r[9]=5678;row=m.start(12,2,r)
        if row['pgc']!=25 or row['registers'][10]!=step or row['registers'][8]!=(1 if step==17 else step+1):raise ValueError('Unexpected Whack cursor cycle')
        cycle.append(row['registers'][9])
    return {'positions':positions,'results':results,'cursorCycle':cycle,'pages':pages}
