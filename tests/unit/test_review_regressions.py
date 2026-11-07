"""Regressions from the single public-release whole-branch review."""

import errno
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/port"))
from export_round import Assets
from export_extras import ExtraAssets
import spu
from tools.owner.prepare import prepare
from tools.owner.importer import SUPPORTED


class ReviewRegressions(unittest.TestCase):
    def test_fresh_prepare_creates_all_analysis_dirs_and_rebuilds_container_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "analysis").mkdir()
            (workspace / "source.json").write_text(
                json.dumps({"sourceFingerprint": SUPPORTED, "source": "fixture"})
            )

            def export_two(source, analysis, public):
                (analysis / "two-player/source-provenance.json").write_text("{}")

            with (
                patch("tools.owner.prepare.source_inventory"),
                patch("tools.owner.prepare.resolve_source"),
                patch("tools.owner.prepare.ensure_toolchain") as ensure,
                patch("export_catalog.export_catalog"),
                patch("export_two_player.export_two_player", side_effect=export_two),
                patch("export_extras.export_gateway", return_value={}),
                patch("export_extras.publish_extras"),
                patch("tools.owner.readiness.seal_prepared"),
            ):
                prepare(workspace, "web")
                ensure.assert_called_once_with(workspace.resolve())

    def test_nondefault_threads_do_not_affect_highlight_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "public"
            (root / "encoding.json").write_text(
                json.dumps(
                    {
                        "crf": 22,
                        "preset": "medium",
                        "audio_bitrate": "96k",
                        "threads": 1,
                        "workers": 1,
                    }
                )
            )
            p = {"palette": [0] * 16}
            assets = Assets(root, root / "analysis", output, {})
            bitmap = {
                "rect": {"x": 0, "y": 0, "width": 1, "height": 1},
                "pixels": [[0]],
            }
            button = {
                "rectangle": [0, 0, 0, 0],
                "colourIndex": 1,
                "colourTable": [[0, 0]],
            }
            with (
                patch.object(assets, "parts", return_value=(p, {})),
                patch.object(assets, "raw", return_value=(root / "raw", b"fixture")),
                patch.object(
                    spu, "extract_packets", return_value=[{"data": b"fixture"}]
                ),
                patch.object(spu, "decode_packet", return_value=bitmap),
            ):
                url = assets.highlight({}, button, "highlight")
            self.assertTrue(
                (output / url.lstrip("/")).read_bytes().endswith(b"IEND\xaeB`\x82")
            )

    def test_interrupted_extras_png_is_regenerated_on_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp)
            assets = SimpleNamespace(
                media=media, parts=lambda ref: ({"palette": [0] * 16}, {})
            )
            bitmap = {
                "rect": {"x": 0, "y": 0, "width": 1, "height": 1},
                "pixels": [[0]],
            }

            def interrupted(path, *args):
                path.write_bytes(b"\x89PNG\r\n\x1a\n")
                raise OSError(errno.ENOSPC, "simulated full disk")

            with patch.object(spu, "write_png", side_effect=interrupted):
                with self.assertRaises(OSError):
                    ExtraAssets(None, assets).raster({}, bitmap, 0)
            url = ExtraAssets(None, assets).raster({}, bitmap, 0)
            self.assertTrue(
                (media / Path(url).name).read_bytes().endswith(b"IEND\xaeB`\x82")
            )

    def test_png_replace_failure_preserves_previous_file_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "image.png"
            spu.write_png(path, 1, 1, b"\x00" * 4)
            before = path.read_bytes()
            with patch.object(
                Path,
                "replace",
                side_effect=OSError(errno.ENOSPC, "simulated replace failure"),
            ):
                with self.assertRaises(OSError):
                    spu.write_png(path, 1, 1, b"\xff" * 4)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(tmp).iterdir()), [path])
