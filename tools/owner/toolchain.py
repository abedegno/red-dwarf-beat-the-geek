"""Build the pinned offline inspectors; dependencies remain outside Git."""

import hashlib
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DVD = ROOT / "tools/dvd"
SHA256 = "a2a18f5ad36d133c74bf9106b6445806fa253b09141a46392550394b647b221e"
URL = (
    "https://download.videolan.org/pub/videolan/libdvdnav/7.0.0/libdvdnav-7.0.0.tar.xz"
)


def doctor():
    required = ["cc", "make", "pkg-config", "ffmpeg", "ffprobe", "node", "npm"]
    missing = [name for name in required if not shutil.which(name)]
    packages = ["dvdread", "dvdnav"] + ([] if sys.platform == "darwin" else ["openssl"])
    if shutil.which("pkg-config"):
        for name in packages:
            if subprocess.run(["pkg-config", "--exists", name]).returncode:
                missing.append("pkg-config:" + name)
    return {"python": sys.version.split()[0], "missing": missing, "ready": not missing}


def ensure_toolchain(workspace):
    status = doctor()
    if not status["ready"]:
        raise RuntimeError(
            "Missing build dependencies: "
            + ", ".join(status["missing"])
            + ". See docs/setup.md."
        )
    workspace = Path(workspace)
    downloads = workspace / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    archive = downloads / "libdvdnav-7.0.0.tar.xz"
    if (
        not archive.exists()
        or hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256
    ):
        pending = archive.with_suffix(".pending")
        try:
            with (
                urllib.request.urlopen(URL, timeout=60) as response,
                pending.open("wb") as output,
            ):
                shutil.copyfileobj(response, output)
            if hashlib.sha256(pending.read_bytes()).hexdigest() != SHA256:
                raise ValueError("libdvdnav download checksum mismatch")
            pending.replace(archive)
        finally:
            pending.unlink(missing_ok=True)
    subprocess.run(["make", "-C", str(DVD), "all"], check=True)
    jobs = [
        ("trace_game", DVD / "trace_game.c"),
        ("round_oracle", ROOT / "tools/port/oracle.c"),
        ("extras_oracle", ROOT / "tools/port/extras_oracle.c"),
    ]
    for name, entry in jobs:
        subprocess.run(
            [
                sys.executable,
                str(DVD / "build_trace.py"),
                str(archive),
                "--entry",
                str(entry),
                "--output",
                str(DVD / "build" / name),
            ],
            check=True,
        )
    return {
        name: str(DVD / "build" / name)
        for name in [
            "inspect_ifo",
            "inspect_nav",
            "trace_game",
            "round_oracle",
            "extras_oracle",
        ]
    }
