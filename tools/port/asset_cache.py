"""Content-bound identities for offline prepared assets, never browser runtime."""
import hashlib
import json
from pathlib import Path


def cache_identity(source_sha256: str, physical_audio: str | None, recipe: dict) -> dict:
    return json.loads(json.dumps({'sourceSha256':source_sha256,'physicalAudio':physical_audio,'recipe':recipe},sort_keys=True))


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def cache_valid(target: Path, identity: dict) -> bool:
    try:
        metadata=json.loads(target.with_suffix(target.suffix+'.cache.json').read_text())
        return metadata['identity']==identity and metadata['outputSha256']==digest(target)
    except (OSError,ValueError,KeyError,TypeError):
        return False


def record_cache(target: Path, identity: dict) -> None:
    metadata=target.with_suffix(target.suffix+'.cache.json')
    temporary=metadata.with_suffix(metadata.suffix+'.tmp')
    temporary.write_text(json.dumps({'identity':identity,'outputSha256':digest(target)},sort_keys=True)+'\n')
    temporary.replace(metadata)


def validate_button_fingerprint(row: dict, expected: str) -> None:
    if row.get('sourceFingerprint')!=expected:
        raise ValueError(f'Button source fingerprint mismatch: {row.get("vob","unknown")} sector {row.get("sector","unknown")}')
