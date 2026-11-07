import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/port'))
FIXTURE=json.loads((Path(__file__).parent/'fixtures/presenters-source.json').read_text())
class PresenterTests(unittest.TestCase):
    def test_profiles_keep_modes_and_presenters_distinct(self):
        from mode_profiles import mode_profile
        for mode,fixture in FIXTURE['hattie'].items():
            value,bonuses=fixture['value'],tuple(fixture['bonus'])
            h=mode_profile(mode,'hattie');n=mode_profile(mode)
            self.assertEqual((h.source_value,h.bonus_pgcs,h.bonus_intro_pgc),(value,bonuses,283))
            self.assertEqual(h.prefix,n.prefix);self.assertEqual(h.labels_file,n.labels_file)
            self.assertNotEqual(h.model_file,n.model_file);self.assertNotEqual(h.dataset_file,n.dataset_file)
            self.assertEqual(mode_profile(h),h)
        with self.assertRaises(ValueError):mode_profile('viewer','unknown')

    def test_hattie_initialization_introductions_and_bonus_paths(self):
        from progression_model import SourceModel
        for mode,value,bonus in [('general-knowledge',10102,291),('viewer',10202,293),('geek',10302,295)]:
            with SourceModel(ROOT/'disc/2EDVD108',ROOT/'analysis',mode,presenter='hattie') as m:
                row=m.start(3,204,mask=1,remaining=7)
                self.assertEqual(row['registers'][0],value);self.assertEqual(row['pgc'],210)
                refs,_,_=m.walk(row,lambda r:r['remaining']!=7)
                self.assertTrue(any(r['pgc']==210 for r in refs))
                for variant in [2,3]:
                    _,q=m.prepare_bonus(variant);self.assertEqual((q['pgc'],q['cell']),(bonus+(variant>=3),2))
                    b=m.bonus(variant);self.assertEqual(b['correct']['gate']['ref']['pgc'],301)
                    self.assertEqual(b['wrong'],b['timeout'])
                self.assertEqual(m.ending(10,6,48,1)['destination'],'bonus')
                setups=m.entry_setups();self.assertEqual({tuple(r['pgc'] for r in setup) for setup in setups},{(9,11,23),(9,12,23),(9,13,23)})

    def test_presenter_menu_groups_match_source_families(self):
        from export_game import presenter_menu_group
        from progression_model import SourceModel
        with SourceModel(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            rows=m.buttons.controls({'vts':2,'domain':'vts-menu','pgc':8,'cell':1})
        self.assertEqual({r['button'] for r in presenter_menu_group(rows,'norman')},set(range(1,9)))
        self.assertEqual({r['button'] for r in presenter_menu_group(rows,'hattie')},set(range(9,17)))

    def test_complete_hattie_models_retain_every_mode_pool_and_distinct_identity(self):
        from progression_model import build_game_model
        for mode in ['general-knowledge','viewer','geek']:
            h=build_game_model(ROOT/'disc/2EDVD108',ROOT/'analysis',mode,presenter='hattie')
            n=build_game_model(ROOT/'disc/2EDVD108',ROOT/'analysis',mode)
            self.assertEqual(h['identity']['presenter'],'hattie')
            self.assertNotEqual(h['identity'],n['identity'])
            self.assertEqual([l['questionPgcs'] for l in h['levels']],[l['questionPgcs'] for l in n['levels']])
            self.assertEqual([len(l['questionPgcs']) for l in h['levels']],[38]*8)
            self.assertTrue(all(h['levels'][i]['intros']!=n['levels'][i]['intros'] for i in range(8)))

    def test_hattie_scorecard_audio_is_the_source_ordering_repeat_carry(self):
        from progression_model import SourceModel
        from export_game import presentation_repeat_offset
        with SourceModel(ROOT/'disc/2EDVD108',ROOT/'analysis',presenter='hattie') as m:
            for vts in range(3,10):
                for score in range(7):
                    p=m.ending(vts,score,score,1)
                    row=m.oracle.call('select 1')
                    self.assertEqual(presentation_repeat_offset(p),row['registers'][9])
                    self.assertEqual(row['registers'][9],3+(0 if score<3 else 1 if score<5 else 2))
