import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.owner.importer import resolve_source, import_source, source_inventory


class ImporterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="btg spaces ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = self.root / "disc" / "VIDEO_TS"
        self.source.mkdir(parents=True)
        (self.source / "VIDEO_TS.IFO").write_bytes(b"fixture")

    def test_resolve_parent_or_video_ts(self):
        self.assertEqual(resolve_source(self.source), self.source)
        self.assertEqual(resolve_source(self.source.parent), self.source)
        with self.assertRaisesRegex(ValueError, "VIDEO_TS.IFO"):
            resolve_source(self.root)

    def test_wrong_disc_and_incomplete_backup_preserve_previous_import(self):
        workspace = self.root / "owner"
        workspace.mkdir()
        old = workspace / "source.json"
        old.write_text("previous")
        with self.assertRaisesRegex(ValueError, "Unsupported|Incomplete"):
            import_source(self.source, workspace)
        self.assertEqual(old.read_text(), "previous")

    def test_inventory_hashes_and_missing_files(self):
        expected = {"VIDEO_TS.IFO": {"bytes": 7, "sha256": "wrong"}}
        with self.assertRaisesRegex(ValueError, "checksum"):
            source_inventory(self.source, expected)
        expected["MISSING.VOB"] = {"bytes": 1, "sha256": "wrong"}
        with self.assertRaises(ValueError):
            source_inventory(self.source, expected)

    def test_failed_tool_leaves_manifest_untouched(self):
        workspace = self.root / "owner"
        workspace.mkdir()
        old = workspace / "source.json"
        old.write_text("previous")
        with (
            patch("tools.owner.importer.source_inventory", return_value={}),
            patch(
                "tools.owner.importer.fingerprint",
                return_value="0876ff298e2cd9ba1e752370ac5e87901b79364126a5126fa0dcf7136fd02c77",
            ),
            patch(
                "tools.owner.importer.ensure_toolchain",
                side_effect=RuntimeError("tool failed"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "tool failed"):
                import_source(self.source, workspace)
        self.assertEqual(old.read_text(), "previous")

    def test_malformed_decoder_output_rejected(self):
        from tools.owner.importer import disassemble

        def decoder(args, **kwargs):
            kwargs["stderr"].write("not a decoded instruction\n")

        with patch("tools.owner.importer.subprocess.run", side_effect=decoder):
            with self.assertRaisesRegex(ValueError, "Malformed"):
                disassemble(Path("decoder"), {"0000000000000000"})

    def test_missing_menu_vob_rejected(self):
        from tools.owner.importer import sha256

        expected = {
            "VIDEO_TS.IFO": {
                "bytes": 7,
                "sha256": sha256(self.source / "VIDEO_TS.IFO"),
            },
            "VTS_02_0.VOB": {"bytes": 2048, "sha256": "not present"},
        }
        with self.assertRaisesRegex(ValueError, "VTS_02_0.VOB"):
            source_inventory(self.source, expected)

    def test_nonstandard_backup_root_fails_before_late_export_path_errors(self):
        renamed = self.root / "renamed backup"
        renamed.mkdir()
        (renamed / "VIDEO_TS.IFO").write_bytes(b"fixture")
        with self.assertRaisesRegex(ValueError, "named VIDEO_TS"):
            resolve_source(renamed)
