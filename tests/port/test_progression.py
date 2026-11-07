import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/port'))
FIXTURE=json.loads((Path(__file__).parent/'fixtures/progression-source.json').read_text())

@unittest.skipUnless((ROOT/'analysis/ifo.json').exists(),'local source inventory required')
class ProgressionTests(unittest.TestCase):
    def test_disc_level_dispatchers_match_independent_source_fixture(self):
        from progression_model import discover_levels
        levels=discover_levels(json.loads((ROOT/'analysis/ifo.json').read_text()))
        self.assertEqual(len(levels),8)
        for actual,want in zip(levels,FIXTURE['levels']):
            for key in ['number','vts','selectorPgcs','introPgc','endingPgc']:
                self.assertEqual(actual[key],want[key],key)

    def test_level_two_route_and_late_timeout_preserve_source_feedback(self):
        from progression_model import SourceModel
        with SourceModel(ROOT/'disc/2EDVD108',ROOT/'analysis') as model:
            route=model.route(4,2,1,42)
            self.assertEqual(route['questionPgc'],112)
            loop=model.timeout(4,112,1,2,42)
            self.assertEqual(loop['kind'],'loop')
            timeout=model.timeout(6,118,1,2,42)
            self.assertEqual(timeout['kind'],'timeout')
            self.assertEqual(timeout['nextCandidateMask'],32)
            self.assertEqual(timeout['refs'],FIXTURE['timeout']['feedback'])

    def test_late_ordering_expires_after_four_plays_and_observation_after_one(self):
        from progression_model import SourceModel
        with SourceModel(ROOT/'disc/2EDVD108',ROOT/'analysis') as model:
            ordered=model.timeout(6,120,1,2,42)
            self.assertEqual(ordered['kind'],'timeout')
            self.assertEqual(ordered['plays'],4)
            observed=model.timeout(6,146,1,2,42)
            self.assertEqual(observed['kind'],'timeout')
            self.assertEqual(observed['plays'],1)

    def test_score_audio_carries_ordering_repeat_offset_into_next_level(self):
        from progression_model import SourceModel
        with SourceModel(ROOT/'disc/2EDVD108',ROOT/'analysis') as model:
            model.ending(5,6,18,1)
            boundary=model.oracle.call('select 1')
            self.assertEqual(boundary['vts'],6)
            self.assertEqual(boundary['registers'][9],2)

    def test_oracle_retains_cumulative_score_before_end_dispatch(self):
        from export_round import Oracle
        oracle=Oracle(ROOT/'disc/2EDVD108')
        try:
            row=oracle.call('start 10 75 1 2 6 0 42 48')
            self.assertEqual(row['registers'][1],10048)
            self.assertEqual(row['cell'],49)
        finally:oracle.close()

class ButtonIndexTests(unittest.TestCase):
    def test_repeated_nav_rows_are_compacted_without_losing_changed_controls(self):
        from button_index import ButtonIndex
        pgc={'vts':4,'domain':'vts-menu','pgc':112,'cells':[{'cell':1,'firstSector':0,'lastSector':100}]}
        row={'vob':'VTS_04_0.VOB','sector':0,'group':1,'button':1,'highlightStart':30000,
             'highlightEnd':300000,'selectionEnd':300000,'rectangle':[1,2,3,4],
             'command':'one','colourIndex':1,'colourTable':[[1,2]],'sourceFingerprint':'source'}
        index=ButtonIndex({'pgcs':[pgc],'sourceFingerprint':'source'},[row,{**row,'sector':1}])
        self.assertEqual(len(index.controls({'vts':4,'pgc':112,'cell':1})),1)
        changed={**row,'sector':2,'command':'changed'}
        index=ButtonIndex({'pgcs':[pgc],'sourceFingerprint':'source'},[row,changed])
        self.assertEqual(len(index.controls({'vts':4,'pgc':112,'cell':1})),2)
        with self.assertRaises(ValueError):
            ButtonIndex({'pgcs':[pgc],'sourceFingerprint':'source'},[{**row,'sourceFingerprint':'wrong'}])

@unittest.skipUnless((ROOT/'analysis/ifo.json').exists(),'local source inventory required')
class PresentationTests(unittest.TestCase):
    def test_continue_retains_outro_and_perfect_total_enters_bonus(self):
        from progression_model import SourceModel
        with SourceModel(ROOT/'disc/2EDVD108',ROOT/'analysis') as model:
            ending=model.ending(3,6,6,1)
            self.assertEqual(ending['destination'],'next-level')
            self.assertEqual(ending['gate']['ref']['pgc'],202)
            self.assertEqual([r['pgc'] for r in ending['gate']['afterRefs']],[86])
            perfect=model.ending(10,6,48,1)
            self.assertEqual(perfect['destination'],'bonus')
            ordinary=model.ending(10,5,47,1)
            self.assertEqual(ordinary['destination'],'complete')
            bonus=model.bonus(2)
            self.assertEqual(bonus['questionRef']['pgc'],285)
            self.assertEqual(bonus['correctChoice'],'A')
            self.assertEqual(bonus['correct']['gate']['ref']['pgc'],301)
            self.assertEqual(bonus['wrong']['destination'],'complete')
            self.assertEqual(bonus['timeout'],bonus['wrong'])

@unittest.skipUnless((ROOT/'disc/2EDVD108').exists(),'local source required')
class OracleResetTests(unittest.TestCase):
    def test_source_entry_default_highlight_does_not_preanswer_ordering_question(self):
        from export_round import Oracle
        oracle=Oracle(ROOT/'disc/2EDVD108')
        try:
            oracle.call('start 3 34 8 3 0 2 42')
            oracle.call('select 2')
            row=oracle.call('start 3 43 256 2 0 2 42')
            self.assertEqual(row['registers'][14],10)  # source initial sentinel: zero selections
        finally:oracle.close()


class FullModelTests(unittest.TestCase):
    @unittest.skipUnless((ROOT/'disc/2EDVD108').exists(),'local source required')
    def test_all_eight_source_pools_and_perfect_bonus_are_normalized(self):
        from progression_model import build_game_model
        model=build_game_model(ROOT/'disc/2EDVD108',ROOT/'analysis')
        self.assertEqual(len(model['levels']),8)
        for level,want in zip(model['levels'],FIXTURE['levels']):
            self.assertEqual(len(level['questionPgcs']),38)
            self.assertEqual(min(level['questionPgcs']),want['firstQuestion'])
            self.assertEqual(max(level['questionPgcs']),want['lastQuestion'])
        self.assertEqual(len(model['bonuses']),2)
        self.assertEqual(model['levels'][0]['answers']['4:4:correct:16384:A-0'][0]['pgc'],119)
        self.assertEqual(model['levels'][-1]['endings']['6:48:1']['destination'],'bonus')
