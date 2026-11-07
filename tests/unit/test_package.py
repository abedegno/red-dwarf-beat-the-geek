import json
from pathlib import Path
import tempfile
import unittest
from tools.owner.package import package_site, validate_package


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.canonical = self.root / "public"
        self.bundle = self.root / "bundle"
        self.target = self.root / "site"
        (self.canonical / "media").mkdir(parents=True)
        (self.canonical / "games").mkdir()
        self.bundle.mkdir()
        (self.bundle / "index.html").write_text("<html>test</html>")
        import struct
        from tools.port.spu import write_png

        def box(kind, body):
            return struct.pack(">I4s", len(body) + 8, kind) + body

        self.video = (
            box(b"ftyp", b"isom" + b"\x00" * 4 + b"isom")
            + box(b"moov", b"fixture movie metadata")
            + box(b"mdat", b"fixture video")
        )
        for name in ["one.mp4", "two.mp4"]:
            (self.canonical / "media" / name).write_bytes(self.video)
        write_png(self.canonical / "media/menu-poster.png", 1, 1, b"\x00" * 4)
        (self.canonical / "media/orphan.mp4").write_bytes(b"orphan")
        self.data = {
            "sourceFingerprint": "fixture",
            "scenes": [{"src": "/media/one.mp4", "id": "x", "durationSeconds": 2}],
            "nested": {"highlightSrc": "/media/two.mp4"},
        }
        (self.canonical / "games/game.json").write_text(json.dumps(self.data))
        self.catalog = {
            "sourceFingerprint": "fixture",
            "modes": {
                "test": {
                    "dataPath": "/games/game.json",
                    "control": {"src": "/media/two.mp4"},
                }
            },
        }
        (self.canonical / "catalog.json").write_text(json.dumps(self.catalog))
        self.seal()

    def seal(self):
        from dataclasses import asdict
        import hashlib
        from tools.owner.encoding import profile
        from tools.owner.readiness import seal_prepared

        for name in ["one.mp4", "two.mp4"]:
            path = self.canonical / "media" / name
            path.with_suffix(".mp4.cache.json").write_text(
                json.dumps(
                    {
                        "identity": {"recipe": "synthetic encoder fixture"},
                        "outputSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
            )
        selected = profile("fidelity")
        (self.canonical.parent / "encoding.json").write_text(
            json.dumps(asdict(selected))
        )
        seal_prepared(self.canonical, selected)

    def test_dedup_recursive_rewrite_and_no_private_files(self):
        result = package_site(self.canonical, self.bundle, self.target)
        validate_package(self.target)
        files = list((self.target / "media").iterdir())
        self.assertEqual(
            len(files), 2
        )  # identical video aliases merge; the fixed poster is retained once
        self.assertFalse(any("orphan" in p.name or "cache" in p.name for p in files))
        catalog = json.loads((self.target / "catalog.json").read_text())
        path = catalog["modes"]["test"]["dataPath"]
        data = json.loads((self.target / path.lstrip("/")).read_text())
        self.assertEqual(data["scenes"][0]["id"], "x")
        self.assertEqual(data["scenes"][0]["durationSeconds"], 2)
        self.assertEqual(data["nested"]["highlightSrc"], data["scenes"][0]["src"])
        self.assertEqual(result["sourceFingerprint"], "fixture")

    def test_missing_traversal_and_limit_fail_preserve_previous(self):
        self.target.mkdir()
        (self.target / "prior").write_text("ready")
        for src in ["/media/missing.mp4", "/media/../../secret.mp4"]:
            self.data["scenes"][0]["src"] = src
            (self.canonical / "games/game.json").write_text(json.dumps(self.data))
            with self.assertRaises(ValueError):
                package_site(self.canonical, self.bundle, self.target)
            self.assertEqual((self.target / "prior").read_text(), "ready")

    def test_corruption_fails_validation(self):
        package_site(self.canonical, self.bundle, self.target)
        (self.target / "index.html").write_text("corrupt")
        with self.assertRaises(ValueError):
            validate_package(self.target)

    def test_limits_and_distinct_same_size_contents(self):
        from unittest.mock import patch

        (self.canonical / "media/two.mp4").write_bytes(self.video[:-1] + b"Z")
        self.seal()
        result = package_site(self.canonical, self.bundle, self.target)
        self.assertEqual(len(list((self.target / "media").glob("*.mp4"))), 2)
        before = (self.target / "manifest.json").read_bytes()
        with patch("tools.owner.manifest.MAX_ASSET_BYTES", 8):
            with self.assertRaisesRegex(ValueError, "25MiB"):
                package_site(self.canonical, self.bundle, self.target)
        self.assertEqual((self.target / "manifest.json").read_bytes(), before)
        with patch("tools.owner.manifest.MAX_FILES", 2):
            with self.assertRaisesRegex(ValueError, "20,000"):
                package_site(self.canonical, self.bundle, self.target)
        self.assertEqual((self.target / "manifest.json").read_bytes(), before)

    def test_damaged_media_or_changed_dataset_cannot_replace_ready_package(self):
        package_site(self.canonical, self.bundle, self.target)
        previous = (self.target / "manifest.json").read_bytes()
        (self.canonical / "media/one.mp4").write_bytes(b"")
        with self.assertRaises(ValueError):
            package_site(self.canonical, self.bundle, self.target)
        self.assertEqual((self.target / "manifest.json").read_bytes(), previous)

    def test_changed_dataset_cannot_be_blessed_by_new_package_checksums(self):
        package_site(self.canonical, self.bundle, self.target)
        previous = (self.target / "manifest.json").read_bytes()
        self.data["scenes"][0]["id"] = "unverified edit"
        (self.canonical / "games/game.json").write_text(json.dumps(self.data))
        with self.assertRaises(ValueError):
            package_site(self.canonical, self.bundle, self.target)
        self.assertEqual((self.target / "manifest.json").read_bytes(), previous)

    def test_hosted_cache_directives_do_not_merge_conflicting_max_ages(self):
        import fnmatch

        package_site(self.canonical, self.bundle, self.target)
        for url in [
            "/media/h-example.mp4",
            "/games/h-example.json",
            "/assets/index.js",
        ]:
            values = []
            pattern = ""
            for line in (self.target / "_headers").read_text().splitlines():
                if line.startswith("/"):
                    pattern = line
                elif line.strip().lower().startswith(
                    "cache-control:"
                ) and fnmatch.fnmatchcase(url, pattern):
                    values.append(line)
            self.assertEqual(len(values), 1, (url, values))
            self.assertIn("immutable", values[0])
            self.assertNotIn("max-age=0", values[0])

    def test_changed_encoding_settings_block_packaging(self):
        package_site(self.canonical, self.bundle, self.target)
        previous = (self.target / "manifest.json").read_bytes()
        path = self.canonical.parent / "encoding.json"
        settings = json.loads(path.read_text())
        settings["crf"] = 28
        path.write_text(json.dumps(settings))
        with self.assertRaisesRegex(ValueError, "settings changed"):
            package_site(self.canonical, self.bundle, self.target)
        self.assertEqual((self.target / "manifest.json").read_bytes(), previous)

    def test_deployment_files_are_readable_outside_encoder_user(self):
        import stat

        for path in (self.canonical / "media").iterdir():
            if path.is_file():
                path.chmod(0o600)
        (self.bundle / "index.html").chmod(0o600)
        package_site(self.canonical, self.bundle, self.target)
        for path in [self.target, *self.target.rglob("*")]:
            self.assertEqual(
                stat.S_IMODE(path.stat().st_mode),
                0o755 if path.is_dir() else 0o644,
                str(path),
            )

    def test_only_referenced_media_and_required_fixed_poster_are_packaged(self):
        from tools.owner.package import strings

        package_site(self.canonical, self.bundle, self.target)
        catalog = json.loads((self.target / "catalog.json").read_text())
        used = {u for u in strings(catalog) if u.startswith("/media/")}
        for url in {u for u in strings(catalog) if u.startswith("/games/")}:
            used.update(
                u
                for u in strings(
                    json.loads((self.target / url.lstrip("/")).read_text())
                )
                if u.startswith("/media/")
            )
        actual = {
            "/" + p.relative_to(self.target).as_posix()
            for p in (self.target / "media").iterdir()
            if p.is_file()
        }
        self.assertEqual(actual, used | {"/media/menu-poster.png"})
