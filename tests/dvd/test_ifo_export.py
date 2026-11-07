import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from fixture import author_disc

ROOT = Path(__file__).resolve().parents[2]


class IfoTests(unittest.TestCase):
    def test_commands_cells_dummy_and_display_aspect(self):
        exporter = ROOT / 'tools/dvd/build/inspect_ifo'
        self.assertTrue(exporter.exists(), 'IFO exporter is not implemented')
        with tempfile.TemporaryDirectory() as tmp:
            disc = author_disc(Path(tmp))
            run = subprocess.run([str(exporter), str(disc)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            data = json.loads(run.stdout)
            self.assertEqual(data['titleSetCount'], 1)
            self.assertEqual(len(data['sourceFingerprint']), 64)
            title = next(p for p in data['pgcs'] if p['domain'] == 'title' and p['pgc'] == 1)
            self.assertEqual(title['commands']['pre'], ['7100000100090000'])
            self.assertEqual(len(title['cells']), 2)
            self.assertLessEqual(title['cells'][0]['lastSector'], title['cells'][1]['firstSector'])
            self.assertEqual(title['display']['aspect'], '16:9')
            dummy = next(p for p in data['pgcs'] if p['domain'] == 'vts-menu' and p['pgc'] == 2)
            self.assertEqual(dummy['cells'], [])
            self.assertEqual(dummy['commands']['pre'], [
                '00b1000000080003', '3003000000010000', '3003000000020000'])
            self.assertTrue(title['commands']['post'])

    def test_missing_disc_fails_without_partial_json(self):
        exporter = ROOT / 'tools/dvd/build/inspect_ifo'
        self.assertTrue(exporter.exists(), 'IFO exporter is not implemented')
        run = subprocess.run([str(exporter), '/nonexistent/disc'], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(run.stdout, '')
