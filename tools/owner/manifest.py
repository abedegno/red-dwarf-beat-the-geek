"""Strict filesystem/URL helpers for generated static sites."""

import hashlib
from pathlib import Path, PurePosixPath

MAX_FILES = 20_000
MAX_ASSET_BYTES = 25 * 1024 * 1024


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def safe_file(root, url):
    path = PurePosixPath(url)
    if (
        not url.startswith("/")
        or ".." in path.parts
        or "\\" in url
        or "?" in url
        or "#" in url
    ):
        raise ValueError("Unsafe package URL: " + url)
    target = (Path(root) / url.lstrip("/")).resolve()
    if not target.is_relative_to(Path(root).resolve()) or not target.is_file():
        raise ValueError("Missing/unsafe package asset: " + url)
    return target


def inventory(root):
    result = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_symlink():
            raise ValueError("Package must not contain symlinks")
        if path.is_file():
            name = path.relative_to(root).as_posix()
            if path.stat().st_size > MAX_ASSET_BYTES:
                raise ValueError("Cloudflare Pages 25MiB asset limit exceeded: " + name)
            result[name] = {"bytes": path.stat().st_size, "sha256": digest(path)}
    if len(result) > MAX_FILES:
        raise ValueError("Cloudflare Pages 20,000 file limit exceeded")
    return result
