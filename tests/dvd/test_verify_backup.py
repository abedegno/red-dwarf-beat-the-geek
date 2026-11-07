import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BackupTests(unittest.TestCase):
    def setUp(self):
        script = ROOT / 'tools/dvd/verify_backup.py'
        self.assertTrue(script.exists(), 'backup verifier is not implemented')
        spec = importlib.util.spec_from_file_location('verify_backup', script)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / 'source'
        self.dst = self.root / 'backup'
        self.src.mkdir()
        self.dst.mkdir()

    def fixture(self, files):
        records = []
        for name, data in files.items():
            for folder in (self.src, self.dst):
                p = folder / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
            records.append({'path': name, 'bytes': len(data)})
        inventory = self.root / 'inventory.json'
        inventory.write_text(json.dumps({'files': records}))
        return inventory

    def test_missing_and_truncated_files_are_incomplete(self):
        inventory = self.fixture({'VIDEO_TS/A.IFO': b'abc', 'VIDEO_TS/B.VOB': b'1234'})
        (self.dst / 'VIDEO_TS/A.IFO').unlink()
        (self.dst / 'VIDEO_TS/B.VOB').write_bytes(b'12')
        result = self.mod.verify_backup(inventory, self.dst, self.src)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual({(e['code'], e['path']) for e in result['errors']},
                         {('missing', 'VIDEO_TS/A.IFO'), ('size', 'VIDEO_TS/B.VOB')})

    def test_changed_metadata_is_reported(self):
        inventory = self.fixture({'VIDEO_TS/A.IFO': b'abc'})
        (self.dst / 'VIDEO_TS/A.IFO').write_bytes(b'xyz')
        result = self.mod.verify_backup(inventory, self.dst, self.src)
        self.assertIn('metadata-mismatch', [e['code'] for e in result['errors']])

    def test_hashes_are_reproducible(self):
        inventory = self.fixture({'VIDEO_TS/A.IFO': b'abc'})
        result = self.mod.verify_backup(inventory, self.dst, self.src)
        self.assertEqual(result['files'][0]['sha256'],
                         'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
        self.assertEqual(result['status'], 'needs-review')
        self.assertFalse(result['errors'])

    def test_scrambled_pes_is_flagged(self):
        sector = bytearray(2048)
        sector[:4] = b'\x00\x00\x01\xba'
        sector[14:21] = b'\x00\x00\x01\xe0\x00\x10\xb0'
        padding = bytearray(sector)
        padding[17] = 0xbe  # Padding packet has no PES flags byte.
        inventory = self.fixture({'VIDEO_TS/A.VOB': bytes(sector + padding)})
        result = self.mod.verify_backup(inventory, self.dst, self.src)
        self.assertEqual(result['files'][0]['scrambledSectors'], 1)
        self.assertIn('scrambled', [e['code'] for e in result['errors']])

    def test_unexpected_file_is_reported(self):
        inventory = self.fixture({'VIDEO_TS/A.IFO': b'abc'})
        (self.dst / 'extra').write_bytes(b'unexpected')
        result = self.mod.verify_backup(inventory, self.dst, self.src)
        self.assertIn('unexpected', [e['code'] for e in result['errors']])

    def test_zero_sectors_are_reported_even_without_scrambling(self):
        inventory = self.fixture({'VIDEO_TS/A.VOB': bytes(4096)})
        result = self.mod.verify_backup(inventory, self.dst, self.src)
        self.assertIn('zero-sectors', [e['code'] for e in result['errors']])
        self.assertEqual(result['files'][0]['zeroRanges'], [[0, 1]])

    def test_placeholder_exception_requires_matching_hash(self):
        sector = bytearray(2048)
        sector[:4] = b'\x00\x00\x01\xba'
        sector[14:21] = b'\x00\x00\x01\xe0\x00\x10\xb0'
        inventory = self.fixture({'VIDEO_TS/A.VOB': bytes(sector), 'VIDEO_TS/A.IFO': b'abc'})
        report = self.mod.verify_backup(inventory, self.dst, self.src)
        digest = next(f['sha256'] for f in report['files'] if f['path'].endswith('.VOB'))
        evidence = {'ripExitStatus': 0, 'logReview': 'resolved',
                    'mediaChecks': [{'exitStatus': 0}],
                    'exceptions': [{'path': 'VIDEO_TS/A.VOB', 'code': 'scrambled',
                                    'sha256': 'wrong', 'classification': 'encrypted-placeholder-retained',
                                    'reason': 'Confirmed navigation-only placeholder; source bytes preserved.'}]}
        self.assertEqual(self.mod.apply_evidence(report, evidence, True)['status'], 'incomplete')
        evidence['exceptions'][0]['sha256'] = digest
        resolved = self.mod.apply_evidence(report, evidence, True)
        self.assertEqual(resolved['status'], 'complete')
        self.assertEqual(len(resolved['reviewedExceptions']), 1)
        self.assertEqual(len(resolved['errors']), 1)  # Never hide original findings.


if __name__ == '__main__':
    unittest.main()
