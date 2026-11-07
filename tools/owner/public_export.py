"""Export an explicit, scanned source snapshot without private working history."""

import json
from pathlib import Path
import re
import shutil
import tempfile
from .manifest import digest

TOP = {
    "README.md",
    "LICENSE",
    "NOTICES.md",
    "CONTRIBUTING.md",
    ".gitignore",
    ".dockerignore",
    "Dockerfile",
}
DOCS = {
    "setup.md",
    "encoding.md",
    "deployment.md",
    "architecture.md",
    "troubleshooting.md",
    "testing.md",
}
APP = {
    "package.json",
    "package-lock.json",
    "index.html",
    "tsconfig.json",
    "vite.config.ts",
    "playwright.config.ts",
}
TEXT = {
    ".py",
    ".c",
    ".h",
    ".json",
    ".ts",
    ".tsx",
    ".css",
    ".html",
    ".md",
    ".yml",
    ".yaml",
    ".toml",
    ".mjs",
}
SECRET = re.compile(
    rb"CLOUDFLARE_API_TOKEN[\"\']?\s*[:=]\s*[\"\'][A-Za-z0-9_-]{20,}[\"\']|(?:^|\n)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|/Users/[A-Za-z0-9_.-]+/",
    re.M,
)


def allowed(relative):
    parts = relative.parts
    name = relative.as_posix()
    if any(
        p in ["node_modules", "build", "__pycache__", ".git"]
        or p.startswith("test-results")
        for p in parts
    ):
        return False
    if len(parts) == 1:
        return name in TOP
    if parts[0] == "docs":
        return (len(parts) == 2 and parts[1] in DOCS) or (
            len(parts) == 3 and parts[1] == "images" and relative.suffix == ".png"
        )
    if parts[0] == "app":
        return (len(parts) == 2 and parts[1] in APP) or (
            parts[1] in ["src", "test", "e2e"] and relative.suffix in TEXT
        )
    if parts[0] == "tools":
        return name == "tools/btg.py" or (
            parts[1] in ["owner", "port", "dvd"]
            and (relative.suffix in TEXT or relative.name == "Makefile")
        )
    if parts[0] == "tests":
        return parts[1] in ["unit", "port", "dvd"] and relative.suffix in TEXT
    if parts[0] == ".github":
        return relative.suffix in [".md", ".yml", ".yaml"]
    if parts[0] == "examples":
        return relative.suffix == ".toml"
    return False


def export_public(source: Path, target: Path):
    source, target = Path(source).resolve(), Path(target).resolve()
    if target.exists():
        raise ValueError("Public export target must be a new directory")
    selected = []
    for directory in [
        source,
        source / "app",
        source / "tools",
        source / "tests",
        source / "docs",
        source / ".github",
        source / "examples",
    ]:
        if not directory.exists():
            continue
        # Top-level files only here; bounded approved subtrees below.
        paths = directory.iterdir() if directory == source else directory.rglob("*")
        for path in paths:
            relative = path.relative_to(source)
            if not allowed(relative):
                continue
            if path.is_symlink():
                raise ValueError(
                    "Public source contains a symlink: " + relative.as_posix()
                )
            if not path.is_file():
                continue
            limit = (
                4 * 1024 * 1024
                if relative.parts[:2] == ("docs", "images")
                else 1024 * 1024
            )
            if path.stat().st_size > limit:
                raise ValueError(
                    "Unexpected large public source file: " + relative.as_posix()
                )
            if path.suffix != ".png":
                data = path.read_bytes()
                try:
                    data.decode("utf-8")
                except UnicodeDecodeError as error:
                    raise ValueError(
                        "Binary public source: " + relative.as_posix()
                    ) from error
                if b"\x00" in data:
                    raise ValueError("Binary public source: " + relative.as_posix())
                if SECRET.search(data):
                    raise ValueError(
                        "Private data pattern in public source: " + relative.as_posix()
                    )
            selected.append((path, relative))
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".public-", dir=target.parent) as pending:
        stage = Path(pending) / "snapshot"
        stage.mkdir()
        manifest = {}
        for path, relative in sorted(set(selected)):
            output = stage / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, output)
            manifest[relative.as_posix()] = digest(output)
        (stage / "public-source.json").write_text(
            json.dumps({"schemaVersion": 1, "files": manifest}, indent=2) + "\n"
        )
        stage.rename(target)
    return {"files": len(manifest)}
