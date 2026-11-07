"""Read-only import of the supported disc into a private owner workspace."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from .toolchain import ROOT, ensure_toolchain
from .workspace import workspace_lock

SUPPORTED = "0876ff298e2cd9ba1e752370ac5e87901b79364126a5126fa0dcf7136fd02c77"


@dataclass(frozen=True)
class SourceInput:
    root: Path
    fingerprint: str


def resolve_source(path: Path) -> Path:
    path = Path(path).expanduser().resolve()
    candidate = path if (path / "VIDEO_TS.IFO").is_file() else path / "VIDEO_TS"
    if not (candidate / "VIDEO_TS.IFO").is_file():
        raise ValueError("Expected VIDEO_TS.IFO in a VIDEO_TS directory or its parent")
    if candidate.name != "VIDEO_TS":
        raise ValueError(
            "The supported backup directory must be named VIDEO_TS; select that directory or its parent"
        )
    return candidate


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(source):
    names = ["VIDEO_TS.IFO"] + [f"VTS_{i:02}_0.IFO" for i in range(1, 16)]
    try:
        entries = [f"VIDEO_TS/{name}:{sha256(source / name)}" for name in names]
    except OSError as error:
        raise ValueError("Incomplete supported backup: missing IFO file") from error
    return hashlib.sha256("\n".join(entries).encode()).hexdigest()


def source_inventory(source, expected=None):
    if expected is None:
        expected = json.loads(
            Path(__file__).with_name("supported-source.json").read_text()
        )
    for name, metadata in expected.items():
        path = source / name
        if not path.is_file() or path.stat().st_size != metadata["bytes"]:
            raise ValueError(
                "Incomplete supported backup: missing or truncated " + name
            )
        if sha256(path) != metadata["sha256"]:
            raise ValueError("Unsupported/damaged source checksum: " + name)
    return expected


def disassemble(binary, codes):
    """Avoid bidirectional pipe backpressure for the large DVD instruction set."""
    with (
        tempfile.TemporaryFile(mode="w+t") as source,
        tempfile.TemporaryFile(mode="w+t") as errors,
    ):
        source.write("\n".join(sorted(codes)) + "\n")
        source.seek(0)
        subprocess.run(
            [str(binary), "--disassemble"],
            stdin=source,
            stdout=subprocess.DEVNULL,
            stderr=errors,
            check=True,
            timeout=30,
        )
        errors.seek(0)
        lines = errors.read().splitlines()
    if len(lines) != len(codes):
        raise ValueError("Malformed pinned disassembly")
    decoded = {}
    for code, line in zip(sorted(codes), lines):
        parts = line.split("\t", 1)
        if len(parts) != 2 or parts[0] != code:
            raise ValueError("Malformed pinned disassembly")
        decoded[code] = parts[1]
    return decoded


def import_source(source: Path, workspace: Path) -> dict:
    source = resolve_source(source)
    workspace = Path(workspace).expanduser().resolve()
    if workspace == source or source in workspace.parents:
        raise ValueError("Workspace must be outside the read-only source directory")
    workspace.mkdir(parents=True, exist_ok=True)
    with workspace_lock(workspace):
        return _import_source(source, workspace)


def _import_source(source, workspace):
    fp = fingerprint(source)
    if fp != SUPPORTED:
        raise ValueError(
            "Unsupported disc fingerprint; this release supports 2EDVD108 only"
        )
    inventory = source_inventory(source)
    binaries = ensure_toolchain(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".import-", dir=workspace) as pending:
        stage = Path(pending)
        with (stage / "ifo.json").open("w") as output:
            subprocess.run(
                [binaries["inspect_ifo"], str(source)],
                stdout=output,
                check=True,
                timeout=60,
            )
        ifo = json.loads((stage / "ifo.json").read_text())
        if ifo["sourceFingerprint"] != fp:
            raise ValueError("Inspector fingerprint mismatch")
        codes = {
            c for p in ifo["pgcs"] for rows in p["commands"].values() for c in rows
        }
        with (stage / "buttons.jsonl").open("w") as output:
            for vob in sorted(source.glob("*_0.VOB")):
                subprocess.run(
                    [binaries["inspect_nav"], str(vob), fp],
                    stdout=output,
                    check=True,
                    timeout=120,
                )
        with (stage / "buttons.jsonl").open() as stream:
            for line in stream:
                codes.add(json.loads(line)["command"])
        ifo["decodedCommands"] = disassemble(binaries["trace_game"], codes)
        sys.path.insert(0, str(ROOT / "tools/port"))
        from source_commands import validate_inventory

        validate_inventory(ifo)
        (stage / "ifo.json").write_text(json.dumps(ifo, separators=(",", ":")) + "\n")
        # Both generated inventories are complete before touching the prior import.
        analysis = workspace / "analysis"
        analysis.mkdir(exist_ok=True)
        for name in ["ifo.json", "buttons.jsonl"]:
            shutil.copy2(stage / name, analysis / (name + ".pending"))
        result = {
            "schemaVersion": 1,
            "source": str(source.parent),
            "videoTs": str(source),
            "sourceFingerprint": fp,
            "files": inventory,
        }
        (stage / "source.json").write_text(json.dumps(result, indent=2) + "\n")
        for name in ["ifo.json", "buttons.jsonl"]:
            (analysis / (name + ".pending")).replace(analysis / name)
        (stage / "source.json").replace(workspace / "source.json")
    return result
