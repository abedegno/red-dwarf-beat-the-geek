import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/port'))
class ExtrasLagerTests(unittest.TestCase):
 def test_source_graph_timed_targets_decoy_and_expiry(self):
  from extras_lager import build_lager
  from extras_source import ExtrasSource
  from export_round import Assets
  with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
   d=build_lager(m,Assets(m.source,m.analysis,ROOT/'app/public',m.pgcs))
  pages={p['id']:p for p in d['pages']}
  # Independently compare every physical NAV epoch, including repetitions,
  # rather than trusting the global compacted ButtonIndex alone.
  import json
  from export_round import activation_rows,nav_origin
  from export_extras import ExtraAssets,menu_ref
  with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
   assets=Assets(m.source,m.analysis,ROOT/'app/public',m.pgcs);extra=ExtraAssets(m,assets)
   rawrows=[]
   with (ROOT/'analysis/buttons.jsonl').open() as stream:
    for line in stream:
     if 'VTS_15_0.VOB' in line:
      row=json.loads(line)
      if row['group']==1:rawrows.append(row)
   for stage in range(1,11):
    ref=menu_ref(15,stage+1);p=m.pgcs[(15,'vts-menu',stage+1)];cell=p['cells'][0]
    rows=[r for r in rawrows if cell['firstSector']<=r['sector']<=cell['lastSector']]
    raw,packets=extra.packets(ref);windows=activation_rows(rows,nav_origin(raw));variants=pages[f'lager-aim-{stage}']['controls'][0]['variants']
    self.assertEqual([(a,b) for _,a,b in windows],[(v['startTicks'],v['endTicks']) for v in variants])
    from timed_spu import display_intervals
    for row,_,_ in windows:
     packet=[p for p in packets if p['stream']==32 and p['pts']<=row['highlightStart']][-1]
     self.assertEqual(len(display_intervals(packet['data'])),1)

  self.assertEqual(len(d['stages']),10);self.assertEqual(len(pages),33)
  self.assertEqual(d['entry'],'lager-intro')
  actions=[]
  for id in d['stages']:
   p=pages[id];self.assertFalse(p['loop']);self.assertEqual(p['after'],{'type':'lager-route','page':'lager-fail','focus':0})
   self.assertEqual(len(p['controls']),1)
   variants=p['controls'][0]['variants'];self.assertGreater(len(variants),0)
   for v in variants:self.assertGreater(v['startTicks'],0);self.assertGreater(v['endTicks'],v['startTicks']);actions.append(v['action']['page'])
  self.assertIn('lager-fail',actions)
  self.assertEqual(pages['lager-transition-10']['after'],{'type':'lager-route','page':'lager-menu','focus':1})
if __name__=='__main__':unittest.main()
