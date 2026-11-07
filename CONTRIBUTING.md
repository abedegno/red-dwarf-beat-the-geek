# Contributing

Run the code-only checks in the README before proposing a change. Include a small
regression test for behavior changes and explain the visible result in your pull
request. Keep changes focused; preserve the original presentation, timings, scoring,
quirks and return paths unless the change explicitly addresses a fidelity defect.

Do not attach disc images, videos, private analysis dumps, API tokens or personal
machine paths to issues or pull requests. Use synthetic fixtures for portable tests.
For source-dependent reports, identify the disc fingerprint, profile, browser and
CLI command, then share the smallest relevant text diagnostic.

New disc editions need independently verified source mapping; weakening fingerprint
checks is not a supported way to import them. Read [the architecture](docs/architecture.md)
and [testing guide](docs/testing.md) before changing the converter.

By contributing original code you agree to license that contribution under
GPL-2.0-or-later. Do not submit third-party game material as newly licensed code.
