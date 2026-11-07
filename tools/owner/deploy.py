"""Verified direct upload to an explicit Cloudflare Pages project."""

import os
from pathlib import Path
import re
import subprocess
from .package import validate_package
from .toolchain import ROOT

WRANGLER = ROOT / "app/node_modules/.bin/wrangler"


def deployment_command(output, project):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,57}", project):
        raise ValueError("Project name must be lowercase letters, numbers and hyphens")
    return [
        str(WRANGLER),
        "pages",
        "deploy",
        "--force",
        str(Path(output).resolve()),
        "--project-name",
        project,
        "--branch",
        "main",
        "--commit-dirty=true",
    ]


def deploy_cloudflare(output, project, dry_run=False, account_id=None):
    manifest = validate_package(output)
    command = deployment_command(output, project)
    result = {
        "fileCount": manifest["fileCount"],
        "bytes": manifest["bytes"],
        "command": command,
    }
    if dry_run:
        return result
    account_id = account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not account_id or not re.fullmatch(r"[a-f0-9]{32}", account_id):
        raise ValueError(
            "Select your account with --account-id (wrangler whoami lists account IDs)."
        )
    if not WRANGLER.is_file():
        raise ValueError("Run npm --prefix app ci to install pinned Wrangler")
    environment = {
        **os.environ,
        "CLOUDFLARE_ACCOUNT_ID": account_id,
        "WRANGLER_SEND_METRICS": "false",
    }
    # Tokens are handled by Wrangler OAuth/environment; never placed in arguments.
    process = subprocess.run(command, env=environment, cwd=ROOT)
    if process.returncode:
        raise RuntimeError(
            "Cloudflare upload failed. Check Wrangler login, account selection and project permissions; the local package is retained."
        )
    return result
