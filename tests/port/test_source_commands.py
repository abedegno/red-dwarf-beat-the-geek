"""Fail closed before reusing a model or touching a playable export."""
import json,shutil,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/port'))
UNKNOWN='e000000000000000'

@unittest.skipUnless((ROOT/'analysis/native-game-model.json').exists(),'local source model required')
class SourceCommandTests(unittest.TestCase):
    def inventory(self):return json.loads((ROOT/'analysis/ifo.json').read_text())

    def modified(self,decoded='WARNING: Unknown instruction type (7)'):
        data=self.inventory()
        pgc=next(p for p in data['pgcs'] if p['vts']==6 and p['domain']=='vts-menu' and p['pgc']==118)
        pgc['commands']['pre'].append(UNKNOWN);data['decodedCommands'][UNKNOWN]=decoded
        return data,pgc

    def test_unknown_question_precommand_is_not_normalized_even_with_spoofed_description(self):
        from export_round import normalize_question
        from progression_model import SourceModel
        with SourceModel(ROOT/'disc/2EDVD108',ROOT/'analysis') as model:
            rows=model.buttons.controls({'vts':6,'domain':'vts-menu','pgc':118,'cell':1})
        for decoded in ['WARNING: Unknown instruction type (7)','Nop']:
            data,pgc=self.modified(decoded)
            with self.subTest(decoded=decoded),self.assertRaisesRegex(ValueError,'Unsupported source command'):
                normalize_question(pgc,rows,data['decodedCommands'])

    def test_cached_and_uncached_unknown_inventory_leave_playable_export_untouched(self):
        from export_game import export_game
        for cached in [False,True]:
            with self.subTest(cached=cached),tempfile.TemporaryDirectory() as root:
                folder=Path(root);analysis=folder/'analysis';analysis.mkdir();out=folder/'public';out.mkdir()
                data,_=self.modified();(analysis/'ifo.json').write_text(json.dumps(data))
                (analysis/'buttons.jsonl').symlink_to(ROOT/'analysis/buttons.jsonl')
                if cached:shutil.copy2(ROOT/'analysis/native-game-model.json',analysis/'native-game-model.json')
                (out/'game.json').write_text('previous playable dataset')
                with patch('progression_model.SourceModel',side_effect=AssertionError('source traversal before validation')),patch('export_game.export_round',side_effect=AssertionError('asset work before validation')):
                    with self.assertRaisesRegex(ValueError,'Unsupported source command'):export_game(ROOT/'disc/2EDVD108',analysis,out)
                self.assertEqual((out/'game.json').read_text(),'previous playable dataset')
                self.assertEqual(sorted(p.name for p in out.iterdir()),['game.json'])

    def test_inventory_change_invalidates_cached_model_even_with_same_source_fingerprint(self):
        from progression_model import build_game_model
        with tempfile.TemporaryDirectory() as root:
            analysis=Path(root);data=self.inventory()
            pgc=next(p for p in data['pgcs'] if p['vts']==6 and p['domain']=='vts-menu' and p['pgc']==118)
            pgc['commands']['pre'].append('0000000000000000')
            (analysis/'ifo.json').write_text(json.dumps(data));(analysis/'buttons.jsonl').symlink_to(ROOT/'analysis/buttons.jsonl')
            shutil.copy2(ROOT/'analysis/native-game-model.json',analysis/'native-game-model.json')
            with patch('progression_model.SourceModel',side_effect=RuntimeError('model rebuild required')):
                with self.assertRaisesRegex(RuntimeError,'model rebuild required'):build_game_model(ROOT/'disc/2EDVD108',analysis)

    def test_validation_dependency_change_invalidates_cached_model(self):
        import asset_cache
        from progression_model import build_game_model
        digest=asset_cache.digest
        def changed(path):
            return 'changed validation policy' if Path(path).name=='asset_cache.py' else digest(path)
        with patch('asset_cache.digest',side_effect=changed),patch('progression_model.SourceModel',side_effect=RuntimeError('model rebuild required')):
            with self.assertRaisesRegex(RuntimeError,'model rebuild required'):
                build_game_model(ROOT/'disc/2EDVD108',ROOT/'analysis')

    def test_oracle_unknown_instruction_warning_is_a_failure(self):
        from export_round import Oracle
        oracle=Oracle(ROOT/'disc/2EDVD108')
        try:
            oracle.call('start 6 118 1 2 0 2 42')
            with self.assertRaisesRegex(RuntimeError,'Unsupported source instruction'):oracle.call('answer '+UNKNOWN)
        finally:oracle.close()
