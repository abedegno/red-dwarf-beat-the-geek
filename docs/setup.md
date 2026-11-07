# Build from your own disc

Supported source: UK PAL **2EDVD108**, fingerprint
`0876ff298e2cd9ba1e752370ac5e87901b79364126a5126fa0dcf7136fd02c77`.
Supply a readable, complete directory named `VIDEO_TS` (uppercase) or its parent. The importer
verifies every required IFO/VOB against the supported edition, reads it without
writing to it, and rejects other editions. It does not rip or decrypt discs.
Keep your original backup separately; the generated website is not a reburnable DVD.

## Native dependencies

Use Node 22.23+ and Python 3.11+. On macOS:

```sh
brew install python node ffmpeg pkg-config libdvdread libdvdnav
```

On Debian/Ubuntu, install Node 22 separately, then:

```sh
sudo apt-get install python3 build-essential pkg-config libdvdread-dev libdvdnav-dev libssl-dev ffmpeg ca-certificates
```

```sh
npm --prefix app ci
python3 tools/btg.py doctor
python3 tools/btg.py import '/path/to/your disc/VIDEO_TS' --workspace owner-workspace
```

`import` downloads and checksum-verifies libdvdnav 7.0.0, builds the pinned offline
inspectors, and generates private inventories. Allow several minutes and network
access for the first build. Keep the selected workspace outside your source backup. The default
`owner-workspace/` is Git-ignored. For another path, keep it outside the checkout
or add it to your `.gitignore` before importing.

## Container toolchain

```sh
docker build -t beat-the-geek .
docker run --rm -v '/path/to/disc:/disc:ro' -v "$PWD/owner-workspace:/work" beat-the-geek import /disc --workspace /work
```

Run later owner commands through the same image and mounts so the recorded source
path remains valid. Docker Desktop needs permission to read the mounted source.

For the complete container workflow, mount the output directory as well:

```sh
mkdir -p owner-workspace exports
docker run --rm -v '/path/to/disc:/disc:ro' -v "$PWD/owner-workspace:/work" beat-the-geek encode --workspace /work --profile web
docker run --rm -v '/path/to/disc:/disc:ro' -v "$PWD/owner-workspace:/work" -v "$PWD/exports:/exports" beat-the-geek build --workspace /work --profile web --output /exports/site
python3 tools/btg.py preview exports/site
```

Mount the output parent (`exports`) and write its child (`site`), allowing atomic
replacement on the mounted filesystem. Do not use a mount point itself as the
`--output` directory. Each disposable encode container ensures its pinned offline
toolchain from the checksum-verified archive in the persistent workspace.

The last command runs the local Python preview on your host. Keep native and
container tool binaries separate; the image contains its own `/project` toolchain.
Do not mount a host checkout over that directory.
