"""Replay keyboard-only maze success/loss paths continuously in the pinned source VM."""
import json
from collections import deque
from pathlib import Path
from extras_source import ExtrasSource

def verify(source=Path('disc/2EDVD108'),analysis=Path('analysis')):
    data=json.loads((analysis/'extras/gateway.json').read_text());maze=data['maze'];pages={p['id']:p for p in data['pages']};provenance=json.loads((analysis/'extras/maze-provenance.json').read_text())
    def transitions(page,focus):
        p=pages[page];controls={c['id']:c for c in p['controls']}
        if p['after'] and p['after']['type']=='maze-route':yield {'type':'SCENE_ENDED'},p['after']
        if focus not in controls:return
        c=controls[focus]
        yield {'type':'ACTIVATE','controlId':focus,'time':1},c['variants'][0]['action']
        for direction,next_focus in c['neighbours'].items():
            target=controls[next_focus];route=target['variants'][0]['action'] if target['autoActivate'] else {'page':page,'focus':next_focus}
            yield {'type':'MOVE','direction':direction,'time':1},route
    def path(goal):
        initial=maze['entry'];queue=deque([(initial['page'],initial['focus'],[])]);seen=set()
        while queue:
            page,focus,events=queue.popleft()
            if (page,focus) in seen:continue
            seen.add((page,focus));node=maze['nodes'].get(page)
            if node and goal(node):return events
            if page=='maze-menu':continue
            for event,route in transitions(page,focus):queue.append((route['page'],route['focus'],events+[event]))
        raise ValueError('No keyboard-only maze path to goal')
    traces=[]
    with ExtrasSource(source,analysis) as m:
        def actual(row):
            if row['vts']!=11:raise ValueError('Maze unexpectedly exited')
            page=next((id for id,p in provenance.items() if p['ref']==m.ref(row) and p['sourceLives']==row['registers'][14]),None)
            if not page:raise ValueError('Source maze state not normalized')
            controls=m.controls(row);ids={c['button'] for c in controls};forced={c['forcedSelect'] for c in controls if c['forcedSelect']};focus=next(iter(forced)) if forced else row['selected'];focus=focus if focus in ids else 0
            return {'page':page,'focus':focus,**maze['nodes'][page]}
        for name,goal in [('success',lambda n:n['victory']),('loss',lambda n:n['lives']==0)]:
            row=m.start(11,17);row=m.activate(row,1);state=actual(row);steps=[]
            for event in path(goal):
                p=pages[state['page']];controls={c['id']:c for c in p['controls']}
                if event['type']=='SCENE_ENDED':row=m.call('cell')
                else:
                    button=controls[state['focus']]['neighbours'][event['direction']] if event['type']=='MOVE' else event['controlId']
                    m.call(f'select {button}')
                    if event['type']=='ACTIVATE' or controls[button]['autoActivate']:row=m.activate(row,button)
                    else:row=m.call('peek')
                state=actual(row);steps.append({'event':event,'expected':state})
            if not goal(state):raise ValueError('Continuous source maze path failed')
            if name=='success' and row['registers'][0]!=47:raise ValueError('Victory failed to change source selection mode')
            traces.append({'name':name,'steps':steps});print('Continuous source maze',name,len(steps),'keyboard/media events',flush=True)
    (analysis/'extras/maze-traces.json').write_text(json.dumps(traces,separators=(',',':'))+'\n');return traces
if __name__=='__main__':verify()
