import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/port'))
class ExtrasWhackTests(unittest.TestCase):
    def test_all_source_appearances_hit_routes_cursor_seeds_and_score_outcomes(self):
        from extras_whack import build_whack
        from extras_source import ExtrasSource
        from export_round import Assets
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            a=Assets(m.source,m.analysis,ROOT/'app/public',m.pgcs);d=build_whack(m,a)
        self.assertEqual(len(d['positions']),17);self.assertEqual(len(d['results']),21)
        self.assertEqual(d['cursorCycle'],[4,5,3,2,7,6,4,9,7,1,5,8,2,3,9,4,1])
        pages={p['id']:p for p in d['pages']};empty=0
        for id in d['positions']:
            p=pages[id];self.assertEqual(len(p['controls']),9);self.assertFalse(p['loop'])
            targets={c['id'] for c in p['controls'] if c['variants'][0]['action']['correct']}
            self.assertLessEqual(len(targets),1);empty+=not bool(targets)
        self.assertEqual(empty,5)
        for id in d['results']:self.assertEqual(pages[id]['after'],{'type':'whack-menu'})
if __name__=='__main__':unittest.main()
