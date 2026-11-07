# Testing

## Public code-only checks

```sh
npm --prefix app ci
npm --prefix app test
python3 -m unittest discover -s tests/unit -v
BTG_BUNDLE_ONLY=1 npm --prefix app run build
```

Portable Vitest tests use synthetic fixtures. Owner-tool unit tests exercise source
validation, profile settings, atomic packaging, public export and deployment
preflight without game media or cloud credentials. The build includes TypeScript
checking. These same commands run in GitHub Actions. A separate Linux job builds the pinned
C toolchain and authors tiny synthetic DVDs with FFmpeg/dvdauthor to test the
inspectors and tracer without commercial disc media.

## Hosted deployment smoke tests

This browser suite reads the target site's catalog and needs no private fixtures:

```sh
cd app
npx playwright install chromium
cd ..
GAME_URL=http://127.0.0.1:4173 npm --prefix app run test:e2e -- deployment.spec.ts --project=chrome
```

It checks eight catalog datasets, HTTP206/404, partial-load failure, both presenters'
first quiz answer and two-player mode menus at original playback speed. Use your
public HTTPS URL for the same checks after deployment. `extras-gateway.spec.ts`
also works against packaged assets and checks captions and Archive navigation.

## Owner data integration

The14 explicit source-dependent native test files are separate. Set `BTG_DATA_ROOT`
to a directory containing `public/` (the canonical prepared profile) and `analysis/`
(the matching private inspection/traces). Missing inputs fail with a clear setup
message; they are never silently skipped. Recorded trace tests also require the
private source-oracle trace fixtures, which normal owner encoding does not create.

```sh
BTG_DATA_ROOT=/absolute/path/to/integration-data npm --prefix app run test:integration
```

The full legacy converter/DVD suites additionally require the repository-local
preservation layout (`disc/2EDVD108`, `analysis`, `app/public` and built C tools).
They are maintainer/source-verification checks, not promised code-only CI:

```sh
python3 tools/port/run_tests.py
python3 -m unittest discover -s tests/dvd -v
```

The other browser tests under `app/e2e/` include long, original-paced full-game checks. Their
source-dependent tests read canonical assets from `app/public`. Install Playwright
browsers with `cd app && npx playwright install`; set `BTG_CHROME_PATH` if you prefer an installed Chrome executable, and point `GAME_URL` at a canonical Vite preview (`npm --prefix app run dev` with prepared assets in
`app/public`). These legacy evidence tests assume canonical filenames; use
`deployment.spec.ts` for the content-addressed hosting package. Enable the
optional WebKit project with `GAME_WEBKIT=1`. Long games can take an hour; disable
tracing for extended runs to avoid large recordings.
