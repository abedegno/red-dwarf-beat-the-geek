import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/port'))
class ExtrasVendingTests(unittest.TestCase):
    def test_original_products_digit_stages_weighted_selection_and_round_tables(self):
        from extras_vending import build_vending
        from extras_source import ExtrasSource
        from export_round import Assets
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            a=Assets(m.source,m.analysis,ROOT/'app/public',m.pgcs);d=build_vending(m,a)
        pages={p['id']:p for p in d['pages']}
        self.assertEqual([len(r['products']) for r in d['rounds']],[3,4,5])
        self.assertEqual([r['randomRange'] for r in d['rounds']],[3,5,5])
        for n,r in enumerate(d['rounds']):
            self.assertEqual([a.scenes[pages[id]['scene']]['durationSeconds'] for id in r['intro']],[4,[3,12,17][n]])
            for product in r['products']:
                self.assertEqual(len(product['pages']),n+2)
                for id in product['pages']:
                    p=pages[id];self.assertTrue(p['loop']);self.assertEqual(len(p['controls']),10)
                    self.assertEqual(sum(c['variants'][0]['action'].get('correct',False) for c in p['controls']),1)
        self.assertEqual(d['rounds'][1]['cueProducts']['5'],d['rounds'][1]['products'][0]['id'])
        self.assertEqual(d['rounds'][2]['cueProducts']['6'],d['rounds'][2]['products'][2]['id'])
        self.assertEqual(d['rounds'][2]['cueProducts']['7'],d['rounds'][2]['products'][3]['id'])
        self.assertEqual(d['initialCues']['2'],2);self.assertEqual(d['initialCues']['4'],3)
        self.assertEqual(d['roundCueOverrides'][0]['4'],3);self.assertEqual(d['roundCueOverrides'][1]['32'],6)
if __name__=='__main__':unittest.main()
