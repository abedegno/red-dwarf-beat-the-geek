import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/port'))
FIXTURE=json.loads((Path(__file__).parent/'fixtures/quiz-modes-source.json').read_text())

class ModeTests(unittest.TestCase):
    def test_profiles_and_selector_families_are_distinct(self):
        from mode_profiles import mode_profile
        from progression_model import discover_levels
        ifo=json.loads((ROOT/'analysis/ifo.json').read_text())
        for name,value,bank,first,later in [('general-knowledge',10101,4,92,14),('viewer',10201,5,95,17),('geek',10301,6,184,68)]:
            p=mode_profile(name);self.assertEqual((p.source_value,p.mask_register),(value,bank))
            levels=discover_levels(ifo,name)
            self.assertEqual(levels[0]['selectorPgcs'],{'2':first,'3':first+1,'4':first+2})
            self.assertEqual(levels[-1]['selectorPgcs'],{'2':later,'3':later+1,'4':later+2})
        with self.assertRaises(ValueError):mode_profile('hattie')

    def test_mode_is_initialized_before_source_question_and_bonus_dispatch(self):
        from progression_model import SourceModel
        for name,value,first,bonus in [('viewer',10201,46,287),('geek',10301,146,289)]:
            with SourceModel(ROOT/'disc/2EDVD108',ROOT/'analysis',name) as model:
                route=model.route(3,2,1,42)
                self.assertEqual(route['questionPgc'],first)
                row=model.start(3,first)
                self.assertEqual(row['registers'][0],value)
                self.assertEqual(row['registers'][5 if name=='viewer' else 6],1)
                _,row=model.prepare_bonus(2);self.assertEqual(row['pgc'],bonus)
                _,row=model.prepare_bonus(3);self.assertEqual(row['pgc'],bonus+1)

    def test_viewer_observation_uses_second_cell_as_prompt(self):
        from progression_model import SourceModel
        with SourceModel(ROOT/'disc/2EDVD108',ROOT/'analysis','viewer') as model:
            self.assertEqual(model.question_layout(3,81),{'prompt':2,'reveal':3})
            route=model.route(3,4,8,42)
            self.assertEqual(route['questionPgc'],81)
            self.assertIn({'vts':3,'domain':'vts-menu','pgc':81,'cell':1,'audio':0},route['introRefs'])
            self.assertEqual(model.timeout(3,81,8,4,42)['kind'],'loop')

    def test_viewer_image_ordering_preserves_four_grid_areas(self):
        from progression_model import SourceModel
        from export_round import normalize_question
        with SourceModel(ROOT/'disc/2EDVD108',ROOT/'analysis','viewer') as model:
            self.assertEqual(model.question_layout(3,65),{'prompt':1,'reveal':2})
            p=model.pgcs[(3,'vts-menu',65)]
            q=normalize_question(p,model.buttons.controls({'vts':3,'pgc':65,'cell':1}),model.ifo['decodedCommands'])
            self.assertEqual(q['correctSequence'],['D','B','C','A'])
            self.assertEqual([(c['rect']['x'],c['rect']['y']) for c in q['choices']],[(126,206),(334,206),(126,366),(333,366)])

    def test_near_identical_source_areas_and_cell_link_reveals_are_preserved(self):
        from progression_model import SourceModel
        from export_round import normalize_question
        with SourceModel(ROOT/'disc/2EDVD108',ROOT/'analysis','viewer') as model:
            self.assertEqual(model.question_layout(3,57),{'prompt':1,'reveal':2})
            p=model.pgcs[(3,'vts-menu',57)]
            q=normalize_question(p,model.buttons.controls({'vts':3,'pgc':57,'cell':1}),model.ifo['decodedCommands'])
            self.assertEqual(len(q['choices']),4)
            self.assertEqual(model.question_layout(9,199),{'prompt':1,'reveal':2})

    def test_all_source_pools_and_bonus_routes_preserve_mode_boundaries(self):
        from progression_model import build_game_model
        seen=set()
        for name in ['viewer','geek']:
            model=build_game_model(ROOT/'disc/2EDVD108',ROOT/'analysis',name)
            self.assertEqual(model['identity']['mode'],name)
            self.assertEqual([len(l['questionPgcs']) for l in model['levels']],[38]*8)
            self.assertEqual([l['questionPgcs'] for l in model['levels']],FIXTURE[name]['pools'])
            if name=='viewer':self.assertEqual(model['levels'][7]['questionPgcs'],[*range(154,191),229])
            else:self.assertEqual(model['levels'][7]['questionPgcs'],list(range(191,229)))
            for level in model['levels']:
                ids={o['questionId'] for options in level['routes'].values() for o in options}
                self.assertFalse(ids&seen);seen|=ids
            self.assertEqual(model['levels'][-1]['endings']['6:48:1']['destination'],'bonus')
            for bonus in model['bonuses']:
                self.assertEqual(bonus['correct']['destination'],'complete')
                self.assertEqual(bonus['timeout'],bonus['wrong'])
                self.assertEqual(bonus['correct']['gate']['ref']['pgc'],301)
