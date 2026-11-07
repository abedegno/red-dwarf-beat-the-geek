"""Owner-facing commands; generated data stays in the selected workspace."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from .importer import import_source
from .toolchain import doctor


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the Red Dwarf DVD game for the web from your own supported backup."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Check native build dependencies")
    p = commands.add_parser(
        "import", help="Verify and inspect a VIDEO_TS backup (read only)"
    )
    p.add_argument("source", type=Path)
    p.add_argument("--workspace", type=Path, required=True)
    p = commands.add_parser(
        "encode", help="Prepare all game modes from imported source"
    )
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--profile", choices=["fidelity", "web"], default="web")
    p.add_argument("--crf", type=int)
    p.add_argument("--preset", choices=["fast", "medium", "slow"])
    p.add_argument("--audio-bitrate")
    p.add_argument("--threads", type=int)
    p.add_argument("--workers", type=int, default=2)
    p = commands.add_parser(
        "build", help="Bundle app and atomically package prepared owner assets"
    )
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--profile", choices=["fidelity", "web"], default="web")
    p.add_argument("--output", type=Path, required=True)
    p = commands.add_parser(
        "validate", help="Verify all package checksums, references and Pages limits"
    )
    p.add_argument("output", type=Path)
    p = commands.add_parser(
        "preview", help="Serve a validated package locally with HTTP Range support"
    )
    p.add_argument("output", type=Path)
    p.add_argument("--port", type=int, default=4173)
    p = commands.add_parser(
        "deploy", help="Upload a validated site to Cloudflare Pages"
    )
    p.add_argument("provider", choices=["cloudflare"])
    p.add_argument("output", type=Path)
    p.add_argument("--project", required=True)
    p.add_argument("--account-id")
    p.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            import os
            from .toolchain import ROOT
            from .package import package_site
            from .workspace import workspace_lock

            with workspace_lock(args.workspace):
                canonical = (
                    args.workspace.resolve() / "profiles" / args.profile / "public"
                )
                if not (canonical.parent / "prepared.json").is_file():
                    raise ValueError("Run encode successfully before build")
                subprocess.run(
                    ["npm", "--prefix", str(ROOT / "app"), "run", "build"],
                    env={**os.environ, "BTG_BUNDLE_ONLY": "1"},
                    check=True,
                )
                result = package_site(canonical, ROOT / "app/dist", args.output)
            print(
                json.dumps(
                    {"fileCount": result["fileCount"], "bytes": result["bytes"]},
                    indent=2,
                )
            )
            return 0
        if args.command in ["validate", "preview"]:
            from .package import validate_package

            result = validate_package(args.output)
            print(f"Verified {result['fileCount']} files; {result['bytes']:,} bytes")
            if args.command == "preview":
                from .preview import serve

                serve(args.output, args.port)
            return 0
        if args.command == "deploy":
            from .deploy import deploy_cloudflare

            result = deploy_cloudflare(
                args.output, args.project, args.dry_run, args.account_id
            )
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "doctor":
            result = doctor()
            print(json.dumps(result, indent=2))
            return 0 if result["ready"] else 1
        if args.command == "encode":
            from .prepare import prepare

            overrides = {
                k: getattr(args, k)
                for k in ["crf", "preset", "audio_bitrate", "threads"]
                if getattr(args, k) is not None
            }
            print(
                "Prepared "
                + str(prepare(args.workspace, args.profile, overrides, args.workers))
            )
            return 0
        if args.command == "import":
            result = import_source(args.source, args.workspace)
            print("Imported supported source " + result["sourceFingerprint"])
            return 0
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        print("btg: " + str(error), file=sys.stderr)
        return 1
    return 0
