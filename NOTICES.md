# Software and original-game material

## Project software

The original software in this repository is licensed under the GNU General Public
License, version 2 or (at your option) any later version (**GPL-2.0-or-later**).
Copyright © 2026 project contributors. See [LICENSE](LICENSE) for the full terms.
Existing SPDX notices in the C tools apply to those files. The offline tools build
against libdvdread and a checksum-pinned libdvdnav 7.0.0 source archive; that archive
and its license/notices stay in the private toolchain workspace and are not vendored
in this repository. React, Vite and the other package dependencies retain their
own licenses and notices in their packages.

## Red Dwarf and the DVD

Red Dwarf: Beat the Geek, its names, characters, footage, performances, audio,
artwork, menus, question text and answers belong to their respective rights holders.
This unofficial project is not affiliated with or endorsed by them.

These source-derived reference files are **not offered under the software license**:

- `tools/port/*labels*.json` and `tools/port/labels.json`: transcribed game captions,
  questions, choices and their source-verification metadata.
- Source-derived examples and expected metadata in `tests/port/fixtures/`.
- `docs/images/*.png`: selected screenshots of the original game presentation,
  included to document this port.

Source hashes, scene coordinates, timing, command inventories and expected outputs
record provenance; they do not change ownership of the underlying game material.
No full DVD image, VOB, game audio/video or generated playable asset package is
included in the source repository or its source releases.

An owner supplies their own supported disc backup for local conversion. The
software license covers this project’s code, not permission to distribute original
game assets. Public deployments containing those assets are separate from this
code repository. Rights holders can contact the maintainer through the repository
for attribution or removal requests.
