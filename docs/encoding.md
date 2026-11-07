# Encoding and resumability

Both profiles encode **from original DVD cells**, with H.264 video, AAC audio,
768×576 square pixels, 25 fps and MP4 faststart. They preserve source durations,
last-frame holds, selected physical audio streams and the original controls and
subtitle times. Transparent control/subtitle PNGs are retained losslessly.

| Profile | Video | Audio | Use |
| --- | --- | --- | --- |
| `fidelity` | CRF18, fast | AAC160k | Accepted preservation settings |
| `web` | CRF22, medium | AAC96k | Smaller static hosting package |

```sh
python3 tools/btg.py encode --workspace owner-workspace --profile fidelity
python3 tools/btg.py encode --workspace owner-workspace --profile web --workers 2
```

The default is two clip workers with two FFmpeg threads each. Use `--workers 1`
on a busy machine; supported range is1–4. Optional `--threads` accepts1–16.
`--crf` accepts16–28; `--preset` accepts fast/medium/slow; `--audio-bitrate` accepts
64k,80k,96k,112k,128k,160k,192k. For example:

```sh
python3 tools/btg.py encode --workspace owner-workspace --profile web --crf 20 --audio-bitrate 128k
```

Resolution/frame-rate changes are deliberately not exposed: they would complicate
fidelity checks. A larger CRF generally reduces file size and picture quality.
Keep fidelity and web outputs in their separate profile directories. Changing
settings invalidates affected clip caches even within the same named profile.

The owner workspace contains private source paths, inspected metadata, raw cell
caches and profile-specific public assets. Keep it out of Git. A verified clip is
reused only when its source digest, audio selection, full encoding recipe, FFmpeg
version and output checksum match. Encoding writes a temporary MP4, probes it and
replaces the clip only after validation. Re-run the same command after interruption;
never treat a partial encode as a complete site. `build` requires a successful
preparation receipt bound to the exact catalog, datasets, media hashes and
encoding settings. Changing those bytes or settings after preparation blocks build
until you run encode again. PNG writes also verify cached bytes and replace files
atomically, so an interrupted image write is repaired on retry.

The deployment packager then removes unreferenced aliases and cache sidecars,
deduplicates equal media contents and rewrites deployment URLs. This saves space
without another lossy encode. Keep `VIDEO_TS` or your ISO separately for preservation.

Four representative source-cell encodes (menu, text question, instructions and a
large motion clip) saved32–52% with the web defaults compared with fidelity. Video
SSIM against fidelity ranged0.968936–0.997191; this is a small benchmark, not a
quality guarantee for every clip. Representative frames were also inspected.

## Measured preparation and hosting size

The supported disc produced a **1.25 GB web package** (3,143 files) and a
**2.36 GB fidelity package** (3,147 files), including the app and datasets.
The largest web asset was 11.2 MB; both packages fit the checked Pages limits.
The web package is about 47% smaller than fidelity after both are deduplicated.
Changing profiles left the catalog and all eight canonical datasets byte-identical;
deployment copies change asset/data URLs only.

On a heavily loaded 14-core Mac with 24 GB RAM, the final web preparation took
65 minutes using verified raw-cell and partial-clip caches; a complete fidelity
cache-resume check took 15 minutes. These are **warm-cache measurements**, not a
complete cold-build benchmark. Allow an hour or more for initial conversion on a
similar busy machine, with additional time for slow source storage. Disk exhaustion
interrupted an earlier run; recovery resumed from verified clips.

The full conversion was verified natively on macOS. Linux container checks covered
a read-only supported-disc import, reconstruction of the first complete quiz
model, 86 real encoded/validated clips in a fresh disposable container, and a
complete static build from a validated portable preparation. Full Linux media
conversion was not repeated.
