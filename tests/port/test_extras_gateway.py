import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/port'))

class ExtrasGatewayExportTests(unittest.TestCase):
    def test_draft_preserves_original_subtitle_timing_and_all_keypad_stages(self):
        from export_extras import build_gateway
        from extras_source import ExtrasSource
        from export_round import Assets
        catalog=(ROOT/'app/public/catalog.json').read_bytes()
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            a=Assets(m.source,m.analysis,ROOT/'app/public',m.pgcs);d=build_gateway(m,a)
            self.assertEqual(len(d['subtitles']),30)
            self.assertEqual(d['subtitles'][0]['startTicks'],180000)
            self.assertEqual(d['subtitles'][0]['endTicks']-d['subtitles'][0]['startTicks'],302080)
            for stage in range(4):
                p=next(p for p in d['pages'] if p['id']==f'keypad-{stage}')
                self.assertTrue(p['loop']);self.assertEqual(len(p['controls']),11)
                for c in p['controls']:
                    for v in c['variants']:
                        self.assertEqual(v['action'],{'type':'main-menu'} if c['id']==11 else {'type':'digit','digit':c['id']%10})
            for id in ['whack-help','vending-help','memory-help','lager-help']:
                page=next(p for p in d['pages'] if p['id']==id)
                if id in ['whack-help','memory-help']:
                    self.assertFalse(page['loop']);self.assertEqual(page['after'],{'type':'stop'})
                else:self.assertTrue(page['loop']);self.assertIsNone(page['after'])
            self.assertEqual(d['codes'],{'7523':'maze','1921':'whack','3598':'vending','9639':'memory','7148':'lager'})
            serialized=json.dumps(d)
            for forbidden in ['registers','command','LinkPGCN','SPRM','bytecode']:self.assertNotIn(forbidden,serialized)
        self.assertEqual((ROOT/'app/public/catalog.json').read_bytes(),catalog)

    def test_instruction_movie_skips_second_title_cell(self):
        from extras_source import ExtrasSource
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            row=m.start(2,26);row=m.activate(row,2)
            self.assertEqual((row['domain'],row['cell']),(2,1))
            row=m.call('cell')
            self.assertEqual((row['vts'],row['domain'],row['pgc']),(2,8,1))

if __name__=='__main__':unittest.main()
