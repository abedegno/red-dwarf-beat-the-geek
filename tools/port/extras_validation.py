"""Complete offline publication gate; runtime validation also runs before play."""
import math,re
GAMES=('maze','whack','vending','memory','lager')
def extras_media(value):
 result=set()
 def walk(v):
  if isinstance(v,str) and v.startswith('/media/'):result.add(v)
  elif isinstance(v,dict):
   for item in v.values():walk(item)
  elif isinstance(v,list):
   for item in v:walk(item)
 walk(value);return result

def validate_extras(d,output,fingerprint):
 try:_validate(d,output,fingerprint)
 except (AssertionError,KeyError,TypeError,AttributeError,IndexError,StopIteration) as e:raise ValueError('Incomplete or invalid original extras data') from e

def _validate(d,output,fingerprint):
 assert d['schemaVersion']==1 and d['sourceFingerprint']==fingerprint
 assert all(d[g] for g in (*GAMES,'quizEntry'))
 pages={p['id']:p for p in d['pages']};scenes={s['id']:s for s in d['scenes']}
 assert len(pages)==len(d['pages']) and len(scenes)==len(d['scenes']) and scenes
 def media(path):
  assert re.fullmatch(r'/media/[a-zA-Z0-9_.-]+',path) and (output/path.lstrip('/')).is_file() and (output/path.lstrip('/')).stat().st_size>0
 def interval(v):
  assert all(isinstance(v[k],(int,float)) and math.isfinite(v[k]) for k in ['startTicks','endTicks']) and 0<=v['startTicks']<v['endTicks']
 def rect(r):assert all(isinstance(r[k],(int,float)) and math.isfinite(r[k]) for k in ['x','y','width','height']) and r['x']>=0 and r['y']>=0 and r['width']>0 and r['height']>0 and r['x']+r['width']<=720 and r['y']+r['height']<=576
 def page(id):assert id in pages
 def action(a):
  t=a['type'];assert t in ['focus','page','main-menu','archive-quit','dispatch-code','stop','instructions','digit','game','maze-route','whack-hit','whack-next','whack-menu','vending-table','vending-order','vending-digit','memory-first','memory-next','memory-choice','memory-stage','lager-route']
  if t in ['page','maze-route','lager-route']:page(a['page'])
  if t in ['digit','vending-digit']:assert type(a['digit']) is int and 0<=a['digit']<=9
  if t=='memory-choice':assert type(a['objectId']) is int and 1<=a['objectId']<=30
  if t=='memory-stage':assert a['stage'] in [0,1,2]
  if t=='instructions':assert type(a['subtitles']) is bool
 for s in scenes.values():media(s['src']);assert math.isfinite(s['durationSeconds']) and s['durationSeconds']>0
 for p in pages.values():
  assert p['scene'] in scenes and type(p['loop']) is bool
  ids={c['id'] for c in p['controls']};assert len(ids)==len(p['controls']) and (p['focus']==0 or p['focus'] in ids)
  if p['after']:action(p['after'])
  for c in p['controls']:
   assert c['label'] and type(c['id']) is int and 1<=c['id']<=36 and type(c['autoActivate']) is bool and c['variants']
   assert all(c['neighbours'][n] in ids for n in ['up','down','left','right'])
   end=-1
   for v in c['variants']:
    interval(v);assert v['startTicks']>=end;end=v['endTicks'];rect(v['rect']);media(v['highlightSrc']);action(v['action'])
    if v['action']['type']=='focus':assert v['action']['controlId'] in ids
 for id in ['instructions-choice','instructions-video','archive-intro',*[f'keypad-{i}' for i in range(4)],'keypad-confirm','invalid-code']:page(id)
 assert len(d['codes'])==5 and set(d['codes'].values())==set(GAMES) and all(re.fullmatch(r'\d{4}',c) for c in d['codes'])
 for g in GAMES:page(d['games'][g]['menuPage']);page(d['games'][g]['instructionPage'])
 for c in d['main'].values():
  rect(c['rect']);media(c['highlightSrc']);assert c['windows']
  for w in c['windows']:interval(w);assert 1<=w['selectionSeed']<=65535
 for s in d['subtitles']:assert s['scene'] in scenes;interval(s);media(s['src'])
 m=d['maze'];page(m['entry']['page']);assert m['nodes']
 for id,n in m['nodes'].items():page(id);assert 0<=n['lives']<=3 and n['docking'] in [1,2,3] and type(n['victory']) is bool
 q=d['quizEntry'];assert len(q['mainOne'])==len(d['main']['instructions']['windows'])
 for p in ['norman','hattie']:assert q['holly'][p]
 for mode in ['viewer','geek','general-knowledge']:assert q['secondMode'][mode]
 for seed in range(1,17):
  for p in ['norman','hattie','two']:assert q['setups'][str(seed)][p] and all(id in scenes for id in q['setups'][str(seed)][p])
 w=d['whack'];assert len(w['positions'])==17 and len(w['results'])==21 and len(w['cursorCycle'])==17
 for id in w['positions']+w['results']:page(id)
 v=d['vending'];assert len(v['rounds'])==3
 for n,r in enumerate(v['rounds']):
  assert len(r['products'])==n+3 and len(r['intro'])==2
  for id in r['intro']+[r['successPage'],r['wrongPage']]:page(id)
  for product in r['products']:
   assert len(product['pages'])==n+2
   for id in product['pages']:page(id)
 page(v['completePage'])
 m=d['memory'];assert len(m['objects'])==30 and len(m['rounds'])==3
 for obj in m['objects']:assert obj['label'];page(obj['page'])
 for n,r in enumerate(m['rounds']):
  assert r['length']==[5,8,12][n] and len(r['recall'])==r['length'] and len(r['results'])==r['length']+1 and r['alwaysCorrectLast']==(n==2)
  for id in [r['intro'],*r['recall'],*r['results']]:page(id)
 l=d['lager'];assert len(l['stages'])==10 and len(set(l['stages']))==10 and len(l['nodes'])==33;page(l['entry'])
 for id in l['stages']:page(id);assert l['nodes'][id]['phase']=='aim'
 for id in l['nodes']:page(id)
 for path in extras_media(d):media(path)
 _validate_routes(d)

def _validate_routes(d):
 pages={p['id']:p for p in d['pages']};owners={};menus=set()
 def claim(id,owner):
  assert id in pages and (id not in owners or owners[id]==owner)
  owners[id]=owner
 for id in ['instructions-choice','instructions-video','archive-intro','keypad-0','keypad-1','keypad-2','keypad-3','keypad-confirm','invalid-code']:claim(id,'gateway')
 for id in GAMES:
  g=d['games'][id];claim(g['menuPage'],id);claim(g['instructionPage'],id);menus.add(g['menuPage'])
 for id in d['maze']['nodes']:claim(id,'maze')
 for id in d['whack']['positions']+d['whack']['results']:claim(id,'whack')
 for r in d['vending']['rounds']:
  for id in [*r['intro'],r['successPage'],r['wrongPage'],*[id for p in r['products'] for id in p['pages']]]:claim(id,'vending')
 claim(d['vending']['completePage'],'vending')
 for o in d['memory']['objects']:claim(o['page'],'memory')
 for r in d['memory']['rounds']:
  for id in [r['intro'],*r['recall'],*r['results']]:claim(id,'memory')
 for id in d['lager']['nodes']:claim(id,'lager')
 def continuation(id,expected):
  a=pages[id]['after'];assert a and all(a.get(k)==v for k,v in expected.items())
 continuation('instructions-video',{'type':'main-menu'});continuation('archive-intro',{'type':'page','page':'keypad-0'});continuation('keypad-confirm',{'type':'dispatch-code'});continuation('invalid-code',{'type':'main-menu'})
 for r in d['vending']['rounds']:
  continuation(r['successPage'],{'type':'vending-order'});continuation(r['wrongPage'],{'type':'page','page':d['games']['vending']['menuPage']})
 continuation(d['vending']['completePage'],{'type':'page','page':d['games']['vending']['menuPage']})
 for stage,r in enumerate(d['memory']['rounds']):
  for score,id in enumerate(r['results']):continuation(id,{'type':'memory-stage','stage':stage+1} if stage<2 and score>=[3,5][stage] else {'type':'page','page':d['games']['memory']['menuPage']})
 for p in pages.values():
  owner=owners.get(p['id']);assert owner and (p['after'] is None if p['loop'] else p['after'] is not None)
  for a in [p['after'],*[v['action'] for c in p['controls'] for v in c['variants']]]:
   if a is None:continue
   t=a['type'];engine=next((id for id in GAMES if t.startswith(id+'-')),None)
   if engine:assert owner==engine
   if t=='page':assert owners.get(a['page'])==owner
   if t=='game':assert p['id'] in menus and a['action']=='play'
   if t=='archive-quit':assert p['id'] in menus
   if t=='instructions':assert p['id']=='instructions-choice'
   if t=='digit':assert re.fullmatch('keypad-[0-3]',p['id'])
   if t=='dispatch-code':assert p['id']=='keypad-confirm'
   if t=='main-menu':assert owner=='gateway'
   if t=='stop':assert owner in ['whack','memory'] and p['id']==d['games'][owner]['instructionPage']
 for id in GAMES:
  g=d['games'][id];menu=pages[g['menuPage']];assert menu['loop']
  def control(id,type,page=None):
   c=next(c for c in menu['controls'] if c['id']==id)
   assert all(v['action']['type']==type and (page is None or v['action'].get('page')==page) for v in c['variants'])
  control(1,'game');control(2 if id=='maze' else 3,'archive-quit')
  if g['instructionPage']!=g['menuPage']:control(2,'page',g['instructionPage'])
