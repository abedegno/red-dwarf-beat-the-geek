import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/port'))

class CacheTests(unittest.TestCase):
    def test_identity_requires_source_stream_recipe_and_output_content(self):
        from asset_cache import cache_identity, cache_valid, record_cache
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'clip.mp4';path.write_bytes(b'correct-media')
            identity=cache_identity('source-digest','0x80',{'codec':'h264','version':1})
            self.assertFalse(cache_valid(path,identity))
            record_cache(path,identity)
            self.assertTrue(cache_valid(path,identity))
            for altered in [cache_identity('different','0x80',{'codec':'h264','version':1}),
                            cache_identity('source-digest','0x81',{'codec':'h264','version':1}),
                            cache_identity('source-digest','0x80',{'codec':'h264','version':2})]:
                self.assertFalse(cache_valid(path,altered))
            path.write_bytes(b'incorrect-xxx')
            self.assertFalse(cache_valid(path,identity))
            path.with_suffix('.mp4.cache.json').write_text('invalid json')
            self.assertFalse(cache_valid(path,identity))

    def test_button_exports_must_identify_the_same_source(self):
        from asset_cache import validate_button_fingerprint
        row={'vob':'VTS_04_0.VOB','sector':123,'sourceFingerprint':'expected'}
        validate_button_fingerprint(row,'expected')
        for altered in [{**row,'sourceFingerprint':'different'}, {k:v for k,v in row.items() if k!='sourceFingerprint'}]:
            with self.assertRaisesRegex(ValueError,'VTS_04_0.VOB.*123'):
                validate_button_fingerprint(altered,'expected')

    def test_raw_cache_corruption_cannot_be_encoded_as_verified_source(self):
        from export_round import Assets
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);source=root/'source';(source/'VIDEO_TS').mkdir(parents=True)
            (source/'VIDEO_TS/VTS_04_0.VOB').write_bytes(b'A'*2048)
            pgc={'vts':4,'domain':'vts-menu','pgc':112,'cells':[{'cell':1,'firstSector':0,'lastSector':0}]}
            assets=Assets(source,root/'analysis',root/'output',{(4,'vts-menu',112):pgc})
            ref={'vts':4,'domain':'vts-menu','pgc':112,'cell':1}
            path,_=assets.raw(ref);path.write_bytes(b'B'*2048)
            path,_=assets.raw(ref)
            self.assertEqual(path.read_bytes(),b'A'*2048)
