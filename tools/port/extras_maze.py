"""Execute and normalize this disc's finite Black Holes maze, offline only."""
from collections import deque
from export_extras import ExtraAssets

def build_maze(m,assets):
    extra=ExtraAssets(m,assets);pending=deque();keys={};snapshots={};pages=[];nodes={};provenance={}
    def focus(row):
        controls=m.controls(row);ids={r['button'] for r in controls};forced={r['forcedSelect'] for r in controls if r['forcedSelect']}
        if len(forced)>1:raise ValueError('Changing maze forced focus')
        value=next(iter(forced)) if forced else row['selected']
        return value if value in ids else 0
    def target(row):
        if row['vts']!=11 or row['domain']!=8:raise ValueError('Unexpected maze domain exit')
        if row['pgc']==17:return {'page':'maze-menu','focus':1}
        key=(row['pgc'],row['cell'],row['registers'][14])
        if key not in keys:
            slot=len(keys)
            if slot>=200:raise ValueError('Unbounded maze graph')
            id=f'maze-route-{slot:03d}';keys[key]=id;snapshots[id]=slot
            m.call(f'save {slot}');pending.append((id,row))
        return {'page':keys[key],'focus':focus(row)}
    row=m.start(11,17);row=m.activate(row,1);entry=target(row)
    while pending:
        id,row=pending.popleft();slot=snapshots[id];ref=m.ref(row);groups={}
        for control in m.controls(row):groups.setdefault(control['button'],[]).append(control)
        actions={}
        for button,group in groups.items():
            commands={r['command'] for r in group}
            if len(commands)!=1:raise ValueError('Timed maze action needs separate normalization')
            m.call(f'restore {slot}');after=m.activate(row,button)
            actions[button]=(f'Pilot position {button}' if len(groups)>2 else 'Continue',{'type':'maze-route',**target(after)})
        m.call(f'restore {slot}');after=m.call('cell');route=target(after)
        same=route['page']==id
        controls=extra.controls(ref,actions) if actions else []
        pages.append({'id':id,'scene':assets.register(ref,'question-loop' if same else 'clip'),'loop':same,'focus':focus(row),'controls':controls,'after':None if same else {'type':'maze-route',**route}})
        pgc=row['pgc'];docking=1 if pgc<=6 else 2 if pgc<=11 else 3
        lives=(0 if pgc==6 else 10-pgc if 7<=pgc<=9 else 17-pgc if 14<=pgc<=16 else row['registers'][14])
        nodes[id]={'lives':lives,'docking':docking,'victory':pgc==12}
        provenance[id]={'ref':ref,'sourceLives':row['registers'][14],'focus':focus(row)}
    (m.analysis/'extras/maze-provenance.json').write_text(__import__('json').dumps(provenance,indent=2)+'\n')
    return {'entry':entry,'nodes':nodes,'pages':pages}
