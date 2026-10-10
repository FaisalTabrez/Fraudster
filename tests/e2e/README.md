# End to end checks

Priya owns browser-level tests after the frozen P0 UI is merged. The bootstrap keeps this directory as the agreed boundary. E2E checks must use fixture mode or local inert URLs, must never open submitted links, and must assert that unavailable coverage and the Demo data badge remain visible.

# Optional real-browser ingestion smoke

This smoke uses only generated synthetic inputs and a fixture-mode gateway.
Its OCR server runs the prepared real English CPU model. All non-local browser
network requests are intercepted and blocked; decoded example URLs are never
visited. Demo analysis output is not model performance. Install optional tools
under ignored `.venv/` (from repository root):

```powershell
npm.cmd install --prefix .venv/e2e --save-exact playwright@1.58.2
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.venv/browsers')
.\.venv\e2e\node_modules\.bin\playwright.cmd install chromium
# In an environment with Pillow and qrcode==8.2:
python tests/e2e/generate_ingestion.py
```

Start the prepared OCR server at 127.0.0.1:8003 (see its README). Start gateway
on 127.0.0.1:8000 with `OCR_SERVICE_URL=http://127.0.0.1:8003` and `DEMO_MODE=true`.
Start Vite at 127.0.0.1:5173 (`npm run dev` in apps/web). Then, from repo root:

```powershell
node tests/e2e/ingestion_smoke.mjs
```

Checks: real OCR/correction/explicit analysis, real local QR text/URL decoding,
no automatic analysis, unsupported payment payload, invalid/no-code images,
cleared stale review, and no external browser requests. It saves a synthetic-only
screenshot under ignored `.venv/`. This opt-in test is separate from model-free
CI and does not require changing existing P0 checks.

## API walkthrough

`demo_walkthrough.py` replays the request-level steps of `docs/demo-script.md` against a running gateway and prints a table of expected and actual results. It needs only the standard library.

```powershell
py -3 tests\e2e\demo_walkthrough.py --base-url http://127.0.0.1:8000 --mode fixture      # gateway with DEMO_MODE=true
py -3 tests\e2e\demo_walkthrough.py --base-url http://127.0.0.1:8000 --mode unavailable  # DEMO_MODE=false, no detectors
```

It does not drive the browser, so the Demo data badge, evidence cards and OCR/QR steps still need the Playwright smoke above or a person.
