import unittest
from tools.owner.encoding import profile


class EncodingTests(unittest.TestCase):
    def test_fidelity_keeps_accepted_recipe(self):
        p = profile("fidelity")
        self.assertEqual(
            (p.crf, p.preset, p.audio_bitrate, p.width, p.height, p.fps, p.threads),
            (18, "fast", "160k", 768, 576, 25, 2),
        )

    def test_profiles_and_overrides_have_distinct_identity(self):
        self.assertNotEqual(profile("fidelity").identity(), profile("web").identity())
        self.assertNotEqual(
            profile("web").identity(),
            profile("web", {"audio_bitrate": "128k"}).identity(),
        )

    def test_reject_unsafe_or_meaning_changing_parameters(self):
        for changes in [
            {"crf": 99},
            {"preset": "bogus"},
            {"audio_bitrate": "-1k"},
            {"threads": 0},
            {"width": 640},
            {"fps": 30},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                profile("web", changes)
        with self.assertRaises(ValueError):
            profile("unknown")

    def test_interrupted_preparation_invalidates_ready_receipt(self):
        import sys, json, tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tools.owner.prepare import prepare
        from tools.owner.importer import SUPPORTED

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/port"))
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "analysis").mkdir()
            (workspace / "source.json").write_text(
                json.dumps(
                    {
                        "sourceFingerprint": SUPPORTED,
                        "source": str(workspace / "source"),
                    }
                )
            )
            output = workspace / "profiles/web"
            output.mkdir(parents=True)
            ready = output / "prepared.json"
            ready.write_text("old complete profile")
            with (
                patch("tools.owner.prepare.source_inventory"),
                patch("tools.owner.prepare.ensure_toolchain"),
                patch("tools.owner.prepare.resolve_source"),
                patch(
                    "export_catalog.export_catalog",
                    side_effect=RuntimeError("interrupted"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "interrupted"):
                    prepare(workspace, "web")
            self.assertFalse(ready.exists())

    def test_failed_encoder_preserves_old_clip_and_cache(self):
        import sys, json, tempfile, subprocess
        from pathlib import Path
        from unittest.mock import patch

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/port"))
        from export_round import Assets

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root / "public"
            (root / "encoding.json").write_text(
                json.dumps(
                    {
                        "crf": 22,
                        "preset": "medium",
                        "audio_bitrate": "96k",
                        "threads": 2,
                        "workers": 1,
                    }
                )
            )
            pgc = {
                "vts": 2,
                "domain": "vts-menu",
                "pgc": 1,
                "audioControl": [0] * 8,
                "cells": [
                    {"cell": 1, "firstSector": 0, "lastSector": 0, "duration": 2}
                ],
            }
            assets = Assets(
                root / "source", root / "analysis", public, {(2, "vts-menu", 1): pgc}
            )
            ref = {"vts": 2, "domain": "vts-menu", "pgc": 1, "cell": 1, "audio": 0}
            id = assets.register(ref)
            target = public / "media" / f"{id}.mp4"
            target.write_bytes(b"prior clip")
            cache = target.with_suffix(".mp4.cache.json")
            cache.write_text("prior cache")

            def probe(args, **kwargs):
                return (
                    "ffmpeg fixture"
                    if args[0] == "ffmpeg"
                    else json.dumps({"streams": [{"codec_type": "video"}]}).encode()
                )

            with (
                patch.object(
                    assets, "raw", return_value=(root / "raw.vob", b"no audio")
                ),
                patch("export_round.subprocess.check_output", side_effect=probe),
                patch(
                    "export_round.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 1, "", "failed"),
                ) as run,
            ):
                with self.assertRaisesRegex(RuntimeError, "failed"):
                    assets.encode((id, ref))
                command = run.call_args.args[0]
                self.assertEqual(command[command.index("-crf") + 1], "22")
                self.assertEqual(command[command.index("-preset") + 1], "medium")
                self.assertIn(
                    "tpad=stop_mode=clone:stop_duration=2",
                    command[command.index("-vf") + 1],
                )
            self.assertEqual(target.read_bytes(), b"prior clip")
            self.assertEqual(cache.read_text(), "prior cache")
