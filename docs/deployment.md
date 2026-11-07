# Hosting

The complete game runs as static files. No server code, database, DVD emulator,
Functions, R2 bucket or custom domain is required. Host the output at a **domain
root**; asset URLs begin with `/`. Never publish the owner workspace or disc backup.

## Prepare and preview

```sh
python3 tools/btg.py build --workspace owner-workspace --profile web --output site
python3 tools/btg.py validate site
python3 tools/btg.py preview site --port 4173
```

The local-only preview supports video byte ranges. Validation checks the checksum
inventory, referenced media, fixed poster, file count and per-asset size. Build also verifies
the completed preparation’s settings and byte hashes before copying assets. Packaging
uses a staged directory; a failed build leaves the previous completed package.
Content-hashed media/datasets receive immutable caching; the entry point, catalog
and fixed poster revalidate. A real404 file avoids an HTML fallback for missing video.

## Cloudflare Pages direct upload

Wrangler is pinned in `app/package-lock.json` and installed by `npm --prefix app ci`.
Sign in interactively and select your account:

```sh
app/node_modules/.bin/wrangler login
app/node_modules/.bin/wrangler whoami
app/node_modules/.bin/wrangler pages project create red-dwarf-beat-the-geek --production-branch main
python3 tools/btg.py deploy cloudflare site --project red-dwarf-beat-the-geek --dry-run
python3 tools/btg.py deploy cloudflare site --project red-dwarf-beat-the-geek --account-id YOUR_ACCOUNT_ID
```

Use a project name unique to your account. If Wrangler lists multiple accounts,
select the intended one when creating the project and pass its ID for upload.
`CLOUDFLARE_ACCOUNT_ID` is an alternative to `--account-id`. Credentials use normal
Wrangler OAuth or `CLOUDFLARE_API_TOKEN` environment authentication; never add tokens
to command arguments, config files, source control or issue reports. The dry run
validates locally and creates no remote resources.

This flow uploads prepared owner assets from your machine. A code-only GitHub
connection cannot reconstruct the game without your private source media. Repeat
build/validate/deploy to update; Pages retains deployment history for rollback.

The packager enforces the documented Free-plan **20,000 files** and **25 MiB per
asset** limits. If a package exceeds either, it fails; choose encoding settings or
another host deliberately. It does not provision storage as a fallback. See
[Pages limits](https://developers.cloudflare.com/pages/platform/limits/) and
[direct upload](https://developers.cloudflare.com/pages/get-started/direct-upload/).

## Other static hosts

Upload the complete `site/` directory together. Require HTTPS, JSON/PNG/MP4 MIME
types and `Range: bytes=…` returning206 for MP4. Translate `_headers` to the host’s
header configuration; do not use a blanket HTML SPA fallback for missing assets.
Check the menu, an Archive game, captions and video seeking after deployment.
