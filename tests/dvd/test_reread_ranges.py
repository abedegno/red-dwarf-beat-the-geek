import importlib.util
import ctypes.util
from unittest.mock import patch
from pathlib import Path
import tempfile
import unittest
from fixture import author_disc

ROOT = Path(__file__).resolve().parents[2]


class RereadTests(unittest.TestCase):
    def load(self):
        path = ROOT / 'tools/dvd/reread_ranges.py'
        self.assertTrue(path.exists(), 'sector rereader is not implemented')
        spec = importlib.util.spec_from_file_location('reread', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_exact_requested_decrypted_range(self):
        mod = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            disc = author_disc(root)
            result = mod.reread_ranges(str(disc), [{'vts': 1, 'domain': 2, 'start': 0, 'count': 2}], root / 'recovered')
            expected = (disc / 'VTS_01_0.VOB').read_bytes()[:4096]
            self.assertEqual(Path(result[0]['file']).read_bytes(), expected)
            self.assertEqual(result[0]['bytes'], 4096)

    def test_out_of_range_does_not_create_recovery_file(self):
        mod = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            disc = author_disc(root)
            with self.assertRaises(ValueError):
                mod.reread_ranges(str(disc), [{'vts': 1, 'domain': 2, 'start': 9999999, 'count': 1}], root / 'recovered')
            self.assertFalse(list((root / 'recovered').glob('*.bin')))

    @unittest.skipUnless(ctypes.util.find_library("dvdcss"), "optional libdvdcss is only needed for physical-disc recovery, not owner backup conversion")
    def test_filesystem_reader_preserves_exact_range(self):
        mod = self.load()
        self.assertTrue(hasattr(mod, 'reread_file'), 'filesystem rereader is not implemented')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            disc = author_disc(root)
            source = disc / 'VTS_01_0.VOB'
            result = mod.reread_file(source, 1, 2)
            self.assertEqual(result, source.read_bytes()[2048:6144])
            with self.assertRaises(ValueError):
                mod.reread_file(source, 9999999, 1)

    def test_missing_optional_css_library_reports_clear_error(self):
        mod = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'sample.VOB'
            source.write_bytes(bytes(4096))
            with patch.object(mod.ctypes.util, 'find_library', return_value=None):
                with self.assertRaisesRegex(RuntimeError, 'libdvdcss is required'):
                    mod.reread_file(source, 0, 1)
