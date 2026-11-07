import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/port'))
class ExtrasMemoryTests(unittest.TestCase):
    def test_source_object_frames_recall_controls_thresholds_and_last_comparison(self):
        from extras_memory import build_memory
        from extras_source import ExtrasSource
        from export_round import Assets
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            a=Assets(m.source,m.analysis,ROOT/'app/public',m.pgcs);d=build_memory(m,a)
        self.assertEqual(len(d['objects']),30);self.assertEqual([r['length'] for r in d['rounds']],[5,8,12])
        self.assertEqual([r['alwaysCorrectLast'] for r in d['rounds']],[False,False,True])
        pages={p['id']:p for p in d['pages']}
        for r in d['rounds']:
            self.assertEqual(len(r['recall']),r['length']);self.assertEqual(len(r['results']),r['length']+1)
            for id in r['recall']:self.assertEqual(len(pages[id]['controls']),30)
        self.assertEqual(pages[d['rounds'][0]['results'][2]]['after'],{'type':'page','page':'memory-menu'})
        self.assertEqual(pages[d['rounds'][0]['results'][3]]['after'],{'type':'memory-stage','stage':1})
        self.assertEqual(pages[d['rounds'][1]['results'][4]]['after'],{'type':'page','page':'memory-menu'})
        self.assertEqual(pages[d['rounds'][1]['results'][5]]['after'],{'type':'memory-stage','stage':2})
        for obj in d['objects']:self.assertTrue(obj['label']);self.assertIn(obj['page'],pages)
if __name__=='__main__':unittest.main()
