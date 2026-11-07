"""Run the established native exporters in profile-isolated private directories."""

from dataclasses import asdict
import json
from pathlib import Path
import sys
from .encoding import profile
from .importer import SUPPORTED, source_inventory, resolve_source
from .workspace import workspace_lock
from .toolchain import ROOT, ensure_toolchain


def prepare(workspace, name, overrides=None, workers=2):
    with workspace_lock(workspace):
        return _prepare(workspace, name, overrides, workers)


def _prepare(workspace, name, overrides=None, workers=2):
    workspace = Path(workspace).resolve()
    if not 1 <= workers <= 4:
        raise ValueError("Workers must be between1 and4")
    source = json.loads((workspace / "source.json").read_text())
    if source.get("sourceFingerprint") != SUPPORTED:
        raise ValueError("Import a supported source first")
    selected = profile(name, overrides)
    source_inventory(resolve_source(Path(source["source"])), source.get("files"))
    ensure_toolchain(workspace)
    output = workspace / "profiles" / name
    output.mkdir(parents=True, exist_ok=True)
    (output / "prepared.json").unlink(missing_ok=True)
    config = {**asdict(selected), "workers": workers}
    pending = output / "encoding.pending"
    pending.write_text(json.dumps(config, indent=2) + "\n")
    pending.replace(output / "encoding.json")
    public = output / "public"
    public.mkdir(exist_ok=True)
    analysis = workspace / "analysis"
    for directory in ["extras", "two-player"]:
        (analysis / directory).mkdir(exist_ok=True)
    sys.path.insert(0, str(ROOT / "tools/port"))
    from export_catalog import export_catalog
    from export_two_player import export_two_player
    from export_extras import export_gateway, publish_extras

    export_catalog(Path(source["source"]), analysis, public)
    export_two_player(Path(source["source"]), analysis, public)
    publish_extras(export_gateway(Path(source["source"]), analysis, public), public)
    from .readiness import seal_prepared

    seal_prepared(public, selected)
    return output
