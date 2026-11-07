"""Source-executed Lager shot windows, decoy, reactions and transitions."""
from export_extras import ExtraAssets,menu_ref

def build_lager(m,assets):
 extra=ExtraAssets(m,assets);pages=[];nodes={};stages=[]
 def name(row):
  pgc,cell=row['pgc'],row['cell']
  if row['vts']!=15 or row['domain']!=8 or row['stopped']:raise ValueError('Unknown Lager exit')
  if pgc==15:return 'lager-menu'
  if pgc in [12,13,14]:return {12:'lager-fail',13:'lager-intro',14:'lager-interlude'}[pgc]
  if 2<=pgc<=11 and cell in [1,2,3]:return 'lager-'+['aim','hit','transition'][cell-1]+'-'+str(pgc-1)
  raise ValueError('Unknown Lager presentation')
 def route(row):
  controls=m.controls(row);ids={c['button'] for c in controls};focus=row['selected'] if row['selected'] in ids else 0
  return {'type':'lager-route','page':name(row),'focus':focus}
 for pgc in range(2,15):
  regs=[0]*16;regs[0]=47;regs[1]=10000;regs[10]=1
  row=m.start(15,pgc,regs);m.call('select 1');row=m.call('peek')
  for cell in range(1,4 if pgc<=11 else 2):
   if row['pgc']!=pgc or row['cell']!=cell:raise ValueError('Lager source skipped an authored cell')
   id=name(row);ref=m.ref(row);controls=m.controls(row);actions={}
   m.call('save 450')
   for button in sorted({c['button'] for c in controls}):
    # ExtraAssets groups actions per button; Lager's decoy is the same button
    # with another command, so each interval is resolved separately below.
    actions[button]=('Fire',{'type':'lager-route','page':'lager-fail','focus':0})
   hit=None
   normalized=extra.controls(ref,actions) if actions else []
   from export_round import activation_rows,nav_origin
   _,raw=assets.raw(ref)
   for c in normalized:
    source=[r for r in controls if r['button']==c['id']]
    windows=activation_rows(source,nav_origin(raw))
    if len(windows)!=len(c['variants']):raise ValueError('Lost Lager source interval')
    for variant,(control,_,_) in zip(c['variants'],windows):
     original=m.call('restore 450');after=m.activate(original,c['id'],control['command']);variant['action']=route(after)
     if after['pgc']==pgc and after['cell']==2:hit=after
   row=m.call('restore 450');after=m.call('cell');ending=route(after)
   phase=['aim','hit','transition'][cell-1] if pgc<=11 else {12:'fail',13:'intro',14:'interlude'}[pgc]
   nodes[id]={'stage':pgc-1 if pgc<=11 else 0,'phase':phase}
   if phase=='aim':stages.append(id)
   pages.append({'id':id,'scene':assets.register(ref),'focus':1 if controls else 0,'loop':False,'controls':normalized,'after':ending});row=hit if cell==1 and pgc<=11 else after
   if row is None:raise ValueError('Missing successful Lager shot')
   if cell==1 and pgc<=11:
    original=m.call('restore 450');correct=next(c for c in controls if m.ifo['decodedCommands'][c['command']].startswith('LinkPGN 2 '));row=m.activate(original,correct['button'],correct['command'])
 return {'entry':'lager-intro','stages':stages,'nodes':nodes,'pages':pages}
