# Architecture

```text
Owner VIDEO_TS (read only)
  → pinned C inspectors + offline DVD navigation oracle
  → normalized semantic game models / source-verified captions
  → original-cell FFmpeg encoding + control/subtitle PNGs
  → profile-specific canonical catalog and datasets
  → Vite app + atomic, content-addressed static package
  → browser React / TypeScript state machines
```

`tools/dvd/` contains the inspectors and pinned libdvdnav builder. `tools/port/`
recovers authored behavior, prepares scenes and exports native datasets.
`tools/owner/` supplies dependency checks, verified import, encoding profiles,
packaging, preview, public-source export and deployment. Generated files belong in
the ignored owner workspace, never the repository.

`app/src/game/` implements quiz progression, mode/presenter choices and two-player
flow. `app/src/extras/` implements the Archive games and source-compatible shared
session context. `app/src/presentation/` displays video and original artwork
controls. Browsers fetch a catalog and eight semantic datasets, then request clips
as play reaches them. No original VM bytecode or libdvdnav runs in the browser.

Canonical media uses scene-oriented IDs for evidence and reproducibility.
Deployment copies use content hashes for immutable caching and byte-identical
deduplication. Packaging changes URL strings only, leaving IDs, questions, choices,
answer tables, durations, source fingerprint and authored routes intact. A fixed
menu-poster alias is retained for the app’s first paint.

Source recognition is intentionally strict. Another edition must be mapped and
verified as its own source profile. A broader DVD emulator would be a different
project; this port models the supported game’s actual authored behavior.
