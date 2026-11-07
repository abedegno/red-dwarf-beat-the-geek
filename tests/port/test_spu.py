import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/dvd'))
from fixture import author_disc


class SpuTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'tools/port/spu.py'
        self.assertTrue(path.exists(), 'SPU decoder is not implemented')
        spec = importlib.util.spec_from_file_location('spu', path)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def test_odd_width_interlaced_bitmap(self):
        # Top row run(5, colour 1); bottom run(2, colour 2), run(3, colour 0).
        pixels = self.mod.decode_rle(bytes.fromhex('15ac'), 5, 2, (0, 1))
        self.assertEqual(pixels, [[1, 1, 1, 1, 1], [2, 2, 0, 0, 0]])

    def test_palette_alpha_and_transparent_pixels(self):
        palette = [0x108080, 0xeb8080] + [0x108080] * 14
        # Pixel 1 uses palette 1 and alpha 15; pixel 2 is transparent.
        rgba = self.mod.render_rgba([[1, 2]], palette, 0x001000f0)
        self.assertEqual(rgba[0:4], bytes([255, 255, 255, 255]))
        self.assertEqual(rgba[7], 0)

    def test_authored_spu_position_and_bitmap(self):
        with tempfile.TemporaryDirectory() as tmp:
            disc = author_disc(Path(tmp), buttons=True)
            packets = self.mod.extract_packets((disc / 'VTS_01_0.VOB').read_bytes())
            self.assertTrue(packets)
            bitmap = self.mod.decode_packet(packets[0]['data'])
            # spumux pads both bitmap dimensions to even sizes.
            self.assertEqual(bitmap['rect'], {'x': 100, 'y': 100, 'width': 122, 'height': 22})
            self.assertTrue(any(any(c != 0 for c in row) for row in bitmap['pixels']))
