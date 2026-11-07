from pathlib import Path
import tempfile
import unittest
from tools.owner.public_export import export_public


class PublicExportTests(unittest.TestCase):
    def test_explicit_source_only_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "private"
            out = root / "public"
            source.mkdir()
            for name, content in [
                ("README.md", "readme"),
                ("tools/port/labels.json", "{}"),
                ("app/src/index.ts", "source"),
                ("docs/images/menu.png", "png"),
                ("analysis/secret.txt", "private"),
                (".env", "token"),
                ("disc/source.VOB", "video"),
                ("docs/superpowers/internal.md", "internal"),
                ("app/public/media/clip.mp4", "media"),
            ]:
                p = source / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
            export_public(source, out)
            self.assertEqual(
                sorted(
                    p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()
                ),
                [
                    "README.md",
                    "app/src/index.ts",
                    "docs/images/menu.png",
                    "public-source.json",
                    "tools/port/labels.json",
                ],
            )

    def test_secrets_and_symlinks_fail_before_export(self):
        for kind in ["secret", "symlink"]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "private"
                source.mkdir()
                p = source / "README.md"
                if kind == "secret":
                    p.write_text("-----BEGIN PRIVATE KEY-----\nfixture")
                else:
                    p.symlink_to("/etc/hosts")
                with self.assertRaises(ValueError):
                    export_public(source, root / "out")
                self.assertFalse((root / "out").exists())

    def test_unintended_binary_or_large_file_fails(self):
        for payload in [b"\x00binary pretending to be code", b"x" * (1024 * 1024 + 1)]:
            with self.subTest(size=len(payload)), tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp) / "source"
                (source / "app/src").mkdir(parents=True)
                (source / "app/src/bad.ts").write_bytes(payload)
                with self.assertRaises(ValueError):
                    export_public(source, Path(tmp) / "out")

    def test_literal_cloudflare_token_assignment_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "README.md").write_text(
                'CLOUDFLARE_API_TOKEN = "' + ("A" * 40) + '"'
            )
            with self.assertRaisesRegex(ValueError, "Private data pattern"):
                export_public(source, Path(tmp) / "out")
