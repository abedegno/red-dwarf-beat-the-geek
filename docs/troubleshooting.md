# Troubleshooting

| Symptom | Action |
| --- | --- |
| Missing data on startup | A code-only build has no playable assets. Import, encode and build an owner package, then preview that directory. |
| Unsupported fingerprint/checksum | Check the exact UK PAL2EDVD108 edition and backup completeness. Do not bypass verification. |
| Missing native dependencies | Run `doctor`; follow [setup](setup.md), including pkg-config development libraries. |
| Long pause before clips appear | Source VM traversal reconstructs thousands of authored routes. Watch the level progress; it can take tens of minutes on first preparation. |
| Conversion interrupted | Re-run the same encode command/profile. Verified clips resume; a partial profile is not ready to publish. |
| Disk full | Preserve your source/ISO first. Remove only unwanted generated profile/site outputs deliberately; do not delete the original backup. Allow roughly20GB for a full owner workflow. |
| Video buffers/stalls | Test the local package, inspect failed network requests and check competing CPU/disk/VM load. Restart a failed session. A past stall’s root cause was not conclusively established. |
| Cloudflare login expired | Run the pinned `wrangler login`, approve in your browser and retry with an explicit account ID. |
| Pages rejects upload | Run `validate`; check asset limits, project/account permissions and authentication. The local ready package is retained. |
| Integration tests fail without files | They intentionally require `BTG_DATA_ROOT`; portable tests need no DVD. See [testing](testing.md). |

Use a current Chromium or Safari/WebKit browser. A user click starts playback,
following browser autoplay rules. Native Safari startup/navigation and representative
WebKit game flows have been checked; every hardware/browser combination, physical
touch device and suspend/resume scenario has not. Report the browser version,
profile, disc fingerprint and a minimal reproducible path through the game.
