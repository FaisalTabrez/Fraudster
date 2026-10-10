# End to end checks

`core_smoke.mjs` is the keyless CI browser check against the packaged fixture-mode origin. It verifies submission, result focus, the permanent Demo data label, absent zero-risk presentation, deceptive-authority URL rendering, and that no request leaves the local web origin. E2E checks use fixture mode or inert URLs and never open submitted links.

With the fixture Compose stack running and Chromium installed through Playwright, run `npm --prefix apps/web run test:e2e` from the repository root.

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

With the model-enabled container stack running, also test the public Nginx
upload boundary (not just Vite or the private gateway):

```powershell
python tests/e2e/upload_limit_smoke.py --base-url http://127.0.0.1:4174/api
```

This pads the generated synthetic PNG to exactly 5,000,000 bytes, verifies OCR
succeeds through the public proxy, and checks that one extra byte receives a
contract-shaped 413 unavailable result. Nginx permits the gateway's bounded
multipart envelope and streams extraction requests instead of buffering uploads
to disk. The test also checks envelope-sized JSON 413 responses and that the
analysis route retains its default 1 MiB proxy limit. Without a model, use
`--expect-ocr-unavailable` to verify an honest 503 instead of extraction success.
The model-free mode uses an embedded synthetic PNG so CI stays hermetic. For a
model-enabled run, the fixture path is resolved from the repository, so the
script can run from another directory; a missing fixture produces a setup
instruction. See
`docs/ingestion-verification.md` for a complete portable Docker override example.
