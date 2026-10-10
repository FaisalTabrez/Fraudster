# OCR and QR integration verification

Run commands from the repository root unless noted. Use Python 3.11 for the
gateway/OCR and Node 24 for the web app. The URL service has its own Python 3.13
environment. Component installation instructions and model provenance are in
`services/ocr/README.md`, `apps/web/src/features/ingestion/README.md`, and
`third_party/manifest.json`.

All smoke inputs are generated synthetic data. Demo analysis proves integration
behavior, not detector accuracy. Missing providers remain unavailable, the
aggregate risk score remains null, and no decoded URL is opened or fetched.

## Component checks

After installing each component's development dependencies, run:

```powershell
python -m pytest -q services/gateway/tests services/text/tests services/ocr/tests tests/integration
# In the URL service's Python 3.13 environment:
python -m pytest -q services/url/tests
# In apps/web, with Node 24:
npm ci
npm run typecheck
npm test
npm run build
```

## Prepare the optional CPU OCR model

Create a separate Python 3.11 environment with the core OCR dependencies first
(see `services/ocr/README.md`). In that environment, from the repository root:

```powershell
python services/ocr/install_model.py
python -m pip check
$env:OCR_MODEL_DIR = (Join-Path (Get-Location) '.venv/review-models')
python -m services.ocr.app.prepare
python -m services.ocr.verify_model
```

Preparation downloads the pinned English model archives on first run and checks
their recorded hashes and extracted files. Downloads require network access;
inference uses the prepared local assets. Keep models and compatibility wheels
under ignored `.venv/`; do not commit them. OCR supports English only and remains
optional. One worker admits one image at a time; review and correct extraction
before analyzing it.

## Reproducible model-enabled Docker setup

After preparing the models, create `.venv/ocr-compose.yaml` with the following
complete contents. `${OCR_MODEL_HOST_DIR}` is supplied below; this override is
local configuration, not an existing repository file.

```yaml
services:
  ocr:
    environment:
      OCR_MODEL_DIR: /service/models
    volumes:
      - type: bind
        source: ${OCR_MODEL_HOST_DIR}
        target: /service/models
        read_only: true
```

Use a separate project and public port to avoid interfering with another stack:

```powershell
$repoRoot = (Get-Location).Path
$env:OCR_MODEL_HOST_DIR = (Resolve-Path '.venv/review-models').Path
$env:WEB_PORT = '4174'
$env:DEMO_MODE = 'true'
docker compose -p fraudster-ingestion-check --profile ocr build --build-arg INSTALL_OCR=true ocr
docker compose -p fraudster-ingestion-check build web gateway text url
docker compose -p fraudster-ingestion-check -f compose.yaml -f .venv/ocr-compose.yaml --profile ocr up -d --no-build --wait --wait-timeout 120
docker compose -p fraudster-ingestion-check -f compose.yaml -f .venv/ocr-compose.yaml exec -T ocr python -m pip check

# Verify real Linux CPU PNG/JPEG inference as the image's non-root user, offline:
docker run --rm --network none --mount "type=bind,source=$repoRoot,target=/workspace,readonly" --mount "type=bind,source=$env:OCR_MODEL_HOST_DIR,target=/models,readonly" -w /workspace -e OCR_MODEL_DIR=/models fraudster-ingestion-check-ocr python -m services.ocr.verify_model
```

The root Compose file is unchanged. The optional image must be built with
`INSTALL_OCR=true`; the default OCR image has no inference dependencies/models.
The override mounts already verified models read-only and does not expose the
private OCR service to the browser.

## Public upload and browser checks

Install Pillow and `qrcode==8.2` in the test environment, then generate inputs:

```powershell
python tests/e2e/generate_ingestion.py
python tests/e2e/upload_limit_smoke.py --base-url http://127.0.0.1:4174/api
python scripts/smoke.py --base-url http://127.0.0.1:4174/api --expect fixture
```

The upload test resolves its fixture from the repository independently of the
current working directory. It checks exactly 5,000,000 bytes reaching real OCR,
one extra image byte rejected by the gateway, and a multipart body above the
5,065,536-byte envelope ceiling rejected by Nginx. Both oversize cases must return
JSON unavailable extraction responses. The separate analysis route retains
Nginx's default 1 MiB body limit and buffering. A model-free stack can use
`--expect-ocr-unavailable`; that checks the 503 unavailable path and never claims
successful extraction.

For real browser OCR correction and local QR decoding, install the optional
Playwright tools as described in `tests/e2e/README.md`, then run:

```powershell
$env:INGESTION_BASE_URL = 'http://127.0.0.1:4174'
$env:PLAYWRIGHT_BROWSERS_PATH = (Join-Path (Get-Location) '.venv/browsers')
node tests/e2e/ingestion_smoke.mjs
```

The browser smoke blocks external requests and verifies explicit review before
analysis, editable OCR, local QR text/URL/colon payloads, unsupported payment
payloads, invalid/no-code images, stale-review clearing, and visible Demo data.
No payment recipient is verified. See the PR verification record for actual
commands, environment versions, and outcomes; these setup instructions do not
assert that a particular run passed.

## Unavailable checks and cleanup

Recreate the gateway with `DEMO_MODE=false` to inspect non-demo behavior. Without
a configured text provider, text analysis must remain unavailable or partial,
with no fixture claim and a null risk score. This is not paid-provider or
real-world performance verification. Production provider setup and retention
terms require separate verification.

Stop only the isolated project when finished:

```powershell
docker compose -p fraudster-ingestion-check -f compose.yaml -f .venv/ocr-compose.yaml --profile ocr down
```
