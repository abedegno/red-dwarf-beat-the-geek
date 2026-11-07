import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from fixture import author_disc

ROOT = Path(__file__).resolve().parents[2]


class NavTests(unittest.TestCase):
    def test_timed_buttons_keep_geometry_commands_and_neighbours(self):
        exporter = ROOT / 'tools/dvd/build/inspect_nav'
        self.assertTrue(exporter.exists(), 'NAV exporter is not implemented')
        with tempfile.TemporaryDirectory() as tmp:
            disc = author_disc(Path(tmp), buttons=True)
            # dvdauthor repeats the first menu button table. Make a controlled
            # second table using the documented PCI layout: GI(60), angles(36),
            # HLI general(22), colours(24), button entries(18 each).
            vob = disc / 'VTS_01_0.VOB'
            raw = bytearray(vob.read_bytes())
            navs = [s for s in range(0, len(raw), 2048)
                    if raw[s + 38:s + 45] == b'\x00\x00\x01\xbf\x03\xd4\x00']
            self.assertGreaterEqual(len(navs), 2)
            pci = navs[-1] + 45
            raw[pci + 98:pci + 102] = (210600).to_bytes(4, 'big')
            button = pci + 142
            raw[button] = (raw[button] & 0xc0) | (90 >> 4)
            raw[button + 1] = (raw[button + 1] & 0x0f) | ((90 & 15) << 4)
            vob.write_bytes(raw)
            result = subprocess.run([str(exporter), str(disc / 'VTS_01_0.VOB')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [json.loads(line) for line in result.stdout.splitlines()]
            one = [r for r in rows if r['button'] == 1]
            self.assertGreaterEqual(len({r['highlightStart'] for r in one}), 2)
            self.assertIn(100, {r['rectangle'][0] for r in one})
            self.assertIn(90, {r['rectangle'][0] for r in one})
            self.assertTrue(all(r['neighbours']['right'] == 2 for r in one))
            self.assertTrue(all(len(r['command']) == 16 for r in one))
            self.assertTrue(all(r['command'] != '0000000000000000' for r in one))

    def test_truncated_sector_is_reported(self):
        exporter = ROOT / 'tools/dvd/build/inspect_nav'
        self.assertTrue(exporter.exists(), 'NAV exporter is not implemented')
        with tempfile.TemporaryDirectory() as tmp:
            vob = Path(tmp) / 'broken.vob'
            vob.write_bytes(b'\x00\x00\x01\xba')
            result = subprocess.run([str(exporter), str(vob)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('truncated', result.stderr)
