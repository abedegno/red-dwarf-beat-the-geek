"""Create an atomic, self-contained deployment from canonical owner assets."""

import json
from pathlib import Path
import shutil
import tempfile
from .manifest import digest, inventory, safe_file
from .readiness import validate_prepared


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def collect_media(value):
    return {url for url in strings(value) if url.startswith("/media/")}


def rewrite(value, paths):
    if isinstance(value, str):
        return paths.get(value, value)
    if isinstance(value, list):
        return [rewrite(item, paths) for item in value]
    if isinstance(value, dict):
        return {key: rewrite(item, paths) for key, item in value.items()}
    return value


def json_bytes(value):
    return (json.dumps(value, separators=(",", ":")) + "\n").encode()


def validate_package(target):
    target = Path(target).resolve()
    manifest = json.loads((target / "manifest.json").read_text())
    actual = inventory(target)
    actual.pop("manifest.json", None)
    if actual != manifest["files"]:
        raise ValueError("Package checksum inventory mismatch")
    if "index.html" not in actual:
        raise ValueError("Missing app bundle")
    catalog = json.loads((target / "catalog.json").read_text())
    documents = [catalog]
    for url in set(u for u in strings(catalog) if u.startswith("/games/")):
        documents.append(json.loads(safe_file(target, url).read_text()))
    for document in documents:
        for url in collect_media(document):
            safe_file(target, url)
    safe_file(target, "/media/menu-poster.png")
    return manifest


def package_site(canonical: Path, bundle: Path, target: Path):
    canonical, bundle, target = map(
        lambda p: Path(p).resolve(), (canonical, bundle, target)
    )
    if any(p == target or p.is_relative_to(target) for p in [canonical, bundle]):
        raise ValueError(
            "Output must not contain canonical inputs or application bundle"
        )
    if (
        target.exists()
        and any(target.iterdir())
        and not (target / "manifest.json").is_file()
    ):
        raise ValueError("Refusing to replace a non-package directory")
    receipt = validate_prepared(canonical)
    catalog = json.loads((canonical / "catalog.json").read_text())
    documents = {
        url: json.loads(safe_file(canonical, url).read_text())
        for url in set(u for u in strings(catalog) if u.startswith("/games/"))
    }
    urls = collect_media(catalog)
    for document in documents.values():
        urls |= collect_media(document)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="." + target.name + "-", dir=target.parent
    ) as temporary:
        stage = Path(temporary) / "site"
        stage.mkdir()
        # Bundle-only Vite output must never include private/public owner assets.
        for source in bundle.rglob("*"):
            if source.is_symlink():
                raise ValueError("Bundle contains symlink")
            if source.is_file():
                relative = source.relative_to(bundle)
                if relative.parts[0] not in ["index.html", "assets"]:
                    raise ValueError("Expected bundle-only Vite output")
                destination = stage / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        (stage / "media").mkdir()
        paths = {}
        for url in sorted(urls):
            source = safe_file(canonical, url)
            extension = source.suffix.lower()
            if extension not in [".mp4", ".png"]:
                raise ValueError("Unexpected media type: " + url)
            name = "/media/h-" + digest(source) + extension
            paths[url] = name
            destination = stage / name.lstrip("/")
            if not destination.exists():
                shutil.copy2(source, destination)
        shutil.copy2(
            safe_file(canonical, "/media/menu-poster.png"),
            stage / "media/menu-poster.png",
        )
        (stage / "games").mkdir()
        import hashlib

        for url, document in sorted(documents.items()):
            payload = json_bytes(rewrite(document, paths))
            name = "/games/h-" + hashlib.sha256(payload).hexdigest() + ".json"
            (stage / name.lstrip("/")).write_bytes(payload)
            paths[url] = name
        (stage / "catalog.json").write_bytes(json_bytes(rewrite(catalog, paths)))
        (stage / "_headers").write_text("""/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
/
  Cache-Control: public, max-age=0, must-revalidate
/index.html
  Cache-Control: public, max-age=0, must-revalidate
/catalog.json
  Cache-Control: public, max-age=0, must-revalidate
/media/menu-poster.png
  Cache-Control: public, max-age=0, must-revalidate
/manifest.json
  Cache-Control: public, max-age=0, must-revalidate
/media/h-*
  Cache-Control: public, max-age=31536000, immutable
/games/h-*
  Cache-Control: public, max-age=31536000, immutable
/assets/*
  Cache-Control: public, max-age=31536000, immutable
""")
        # A top-level404 disables Pages' automatic SPA fallback for missing media.
        (stage / "404.html").write_text(
            "<!doctype html><title>Not found</title><p>File not found.</p>"
        )
        files = inventory(stage)
        manifest = {
            "schemaVersion": 1,
            "sourceFingerprint": catalog.get("sourceFingerprint"),
            "encodingProfile": receipt["profile"],
            "profileIdentity": receipt["identity"],
            "files": files,
            "fileCount": len(files) + 1,
            "bytes": sum(f["bytes"] for f in files.values()),
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        # Public artifacts must remain readable when a disposable container's
        # root-owned private caches are previewed/uploaded by the host user.
        stage.chmod(0o755)
        for path in stage.rglob("*"):
            path.chmod(0o755 if path.is_dir() else 0o644)
        validate_package(stage)
        previous = Path(temporary) / "previous"
        if target.exists():
            target.rename(previous)
        try:
            stage.rename(target)
        except BaseException:
            if previous.exists():
                previous.rename(target)
            raise
    return manifest
