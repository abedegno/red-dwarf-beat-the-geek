import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/port'))
class ExtrasQuizEntryTests(unittest.TestCase):
    def test_deterministic_setup_and_menu_variant_seeds_are_recovered_from_the_vm(self):
        from extras_quiz import build_quiz_entries
        from extras_source import ExtrasSource
        from export_round import Assets
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            a=Assets(m.source,m.analysis,ROOT/'app/public',m.pgcs);d=build_quiz_entries(m,a)
        self.assertEqual(set(d['holly']),{'norman','hattie'})
        self.assertEqual(set(d['secondMode']),{'viewer','geek','general-knowledge'})
        self.assertGreaterEqual(len(d['setups']),10)
        for routes in [*d['holly'].values(),*d['secondMode'].values()]:
            self.assertTrue(routes)
            for route in routes:self.assertIn(route['variantCue'],[1,2,3,4])
        for setups in d['setups'].values():
            self.assertEqual(set(setups),{'norman','hattie','two'})
            self.assertTrue(all(len(s)==3 for s in setups.values()))
if __name__=='__main__':unittest.main()
