"""Bind a completed preparation to validated runtime bytes and encoder settings."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import struct
import zlib
from .encoding import profile
from .manifest import digest, safe_file


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def runtime_files(canonical):
    canonical = Path(canonical)
    catalog = json.loads((canonical / "catalog.json").read_text())
    if not isinstance(catalog, dict) or not catalog.get("sourceFingerprint"):
        raise ValueError("Invalid prepared catalog")
    documents = [catalog]
    urls = {"/catalog.json", "/media/menu-poster.png"}
    for url in {u for u in strings(catalog) if u.startswith("/games/")}:
        document = json.loads(safe_file(canonical, url).read_text())
        if not isinstance(document, dict) or document.get(
            "sourceFingerprint"
        ) != catalog.get("sourceFingerprint"):
            raise ValueError("Prepared dataset source fingerprint mismatch: " + url)
        urls.add(url)
        documents.append(document)
    for document in documents:
        urls.update(u for u in strings(document) if u.startswith("/media/"))
    return catalog, {url.lstrip("/"): safe_file(canonical, url) for url in sorted(urls)}


def validate_png(path):
    data = Path(path).read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Invalid prepared PNG: " + str(path))
    offset = 8
    chunks = []
    compressed = bytearray()
    ended = False
    dimensions = None
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("Truncated prepared PNG: " + str(path))
        body = data[offset + 8 : offset + 8 + length]
        crc = struct.unpack(">I", data[offset + 8 + length : end])[0]
        if zlib.crc32(kind + body) != crc:
            raise ValueError("Prepared PNG checksum mismatch: " + str(path))
        if not chunks and kind != b"IHDR":
            raise ValueError("Missing prepared PNG header")
        if kind == b"IHDR":
            if dimensions is not None or len(body) != 13:
                raise ValueError("Invalid prepared PNG dimensions")
            width, height, depth, colour, compression, filtering, interlace = (
                struct.unpack(">IIBBBBB", body)
            )
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(colour)
            if (
                not channels
                or depth != 8
                or compression
                or filtering
                or interlace
                or not 0 < width <= 4096
                or not 0 < height <= 4096
            ):
                raise ValueError("Unsupported prepared PNG format")
            dimensions = (width, height, channels)
        elif kind == b"IDAT":
            compressed.extend(body)
        elif kind == b"IEND":
            if length or end != len(data):
                raise ValueError("Invalid prepared PNG end")
            ended = True
            offset = end
            break
        chunks.append(kind)
        offset = end
    if not ended or not dimensions or not compressed:
        raise ValueError("Incomplete prepared PNG: " + str(path))
    width, height, channels = dimensions
    expected = height * (1 + width * channels)
    decoder = zlib.decompressobj()
    try:
        raw = decoder.decompress(bytes(compressed), expected + 1)
    except zlib.error as error:
        raise ValueError("Invalid prepared PNG pixels") from error
    if len(raw) != expected or not decoder.eof or decoder.unused_data:
        raise ValueError("Truncated prepared PNG pixels")


def validate_mp4(path):
    path = Path(path)
    size = path.stat().st_size
    boxes = []
    offset = 0
    with path.open("rb") as source:
        while offset + 8 <= size:
            source.seek(offset)
            header = source.read(8)
            length, kind = struct.unpack(">I4s", header)
            header_size = 8
            if length == 1:
                extended = source.read(8)
                if len(extended) != 8:
                    raise ValueError("Truncated prepared MP4")
                length = struct.unpack(">Q", extended)[0]
                header_size = 16
            elif length == 0:
                length = size - offset
            if length < header_size or offset + length > size:
                raise ValueError("Truncated prepared MP4: " + str(path))
            boxes.append(kind)
            offset += length
    if (
        offset != size
        or not boxes
        or boxes[0] != b"ftyp"
        or b"moov" not in boxes
        or b"mdat" not in boxes
    ):
        raise ValueError("Invalid prepared MP4: " + str(path))
    try:
        cache = json.loads(path.with_suffix(".mp4.cache.json").read_text())
        if not isinstance(cache["identity"], dict) or cache["outputSha256"] != digest(
            path
        ):
            raise ValueError("mismatch")
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError(
            "Prepared MP4 does not match its validated encoder cache: " + path.name
        ) from error


def seal_prepared(canonical, selected):
    canonical = Path(canonical)
    catalog, paths = runtime_files(canonical)
    files = {}
    for name, path in paths.items():
        if path.suffix == ".mp4":
            validate_mp4(path)
        elif path.suffix == ".png":
            validate_png(path)
        files[name] = {"bytes": path.stat().st_size, "sha256": digest(path)}
    receipt = {
        "schemaVersion": 2,
        "profile": asdict(selected),
        "identity": selected.identity(),
        "sourceFingerprint": catalog["sourceFingerprint"],
        "files": files,
    }
    pending = canonical.parent / "prepared.pending"
    pending.write_text(json.dumps(receipt, indent=2) + "\n")
    pending.replace(canonical.parent / "prepared.json")
    return receipt


def validate_prepared(canonical):
    canonical = Path(canonical)
    try:
        receipt = json.loads((canonical.parent / "prepared.json").read_text())
        settings = json.loads((canonical.parent / "encoding.json").read_text())
        if not isinstance(receipt, dict) or not isinstance(settings, dict):
            raise ValueError("Invalid preparation receipt/settings")
        recorded = receipt["profile"]
        name = recorded["name"]
        selected = profile(
            name, {key: value for key, value in recorded.items() if key != "name"}
        )
        if (
            receipt.get("schemaVersion") != 2
            or receipt["identity"] != selected.identity()
            or any(settings.get(k) != v for k, v in recorded.items())
        ):
            raise ValueError("Preparation settings changed; re-run encode")
        catalog, paths = runtime_files(canonical)
        actual = {
            name: {"bytes": path.stat().st_size, "sha256": digest(path)}
            for name, path in paths.items()
        }
        if (
            receipt["sourceFingerprint"] != catalog["sourceFingerprint"]
            or actual != receipt["files"]
        ):
            raise ValueError(
                "Prepared runtime files changed; re-run encode before build"
            )
        return receipt
    except (OSError, KeyError, TypeError) as error:
        raise ValueError(
            "Missing/incomplete validated preparation; run encode before build"
        ) from error
