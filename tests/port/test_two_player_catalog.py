import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/port'))
class TwoPlayerCatalogTests(unittest.TestCase):
    def test_republishing_keeps_existing_immutable_data_untouched(self):
        from export_two_player import publish_two_player
        data=json.loads((ROOT/'app/public/two-player.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp);(output/'media').symlink_to(ROOT/'app/public/media',target_is_directory=True)
            (output/'catalog.json').write_text(json.dumps({'sourceFingerprint':data['sourceFingerprint'],'schemaVersion':2}))
            publish_two_player(data,output)
            target=next((output/'games').glob('two-player-*.json'));before=target.stat().st_mtime_ns
            publish_two_player(data,output)
            self.assertEqual(target.stat().st_mtime_ns,before)

    def test_mismatched_source_cannot_replace_accepted_catalog(self):
        from export_two_player import publish_two_player
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp);old=b'{"sourceFingerprint":"accepted","schemaVersion":2}\n'
            (output/'catalog.json').write_bytes(old)
            with self.assertRaises(ValueError):publish_two_player({'sourceFingerprint':'other'},output)
            self.assertEqual((output/'catalog.json').read_bytes(),old)
            self.assertFalse((output/'two-player.json').exists())
