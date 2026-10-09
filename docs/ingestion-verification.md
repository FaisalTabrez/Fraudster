# Ingestion handoff evidence (#9, #10)

Branch: `feat/ingestion`, based on origin/main `fb581bbe6e3d1349d75e75db6f4e188b172a2cfe`.
Tested 2026-10-09 on Windows x64 build 26200, Python 3.11.17, Node 24.14.1,
npm 11.11.0. Optional browser smoke used Playwright 1.58.2 / Chromium 145.

## Commands and actual results

Commands below ran from repository root unless a directory is stated. The local
Python environments are under ignored `.venv/`, with dependencies installed from
the component manifests. No downloaded model or generated input is committed.

| Exact command | Actual outcome |
| --- | --- |
| `.\.venv\Scripts\uv.exe pip install --python .venv\test\Scripts\python.exe -r services\gateway\requirements-dev.txt -r services\ocr\requirements-dev.txt` | Passed; model-free component environment |
| `.\.venv\test\Scripts\python.exe -m pytest -q services\gateway\tests services\text\tests services\ocr\tests tests\integration --basetemp=.venv\pytest-temp --tb=short` | 40 passed |
| `npm.cmd ci` (apps/web) | Passed; lockfile install, zero audit vulnerabilities; existing jsdom dependencies warn that Node >=24.15 is preferred |
| `npm.cmd run typecheck` (apps/web) | Passed |
| `npm.cmd test` (apps/web) | 26 passed across 4 files |
| `npm.cmd run build` (apps/web) | Passed; main JS ~234 kB, optional ZXing chunk ~477 kB |
| `.\.venv\Scripts\uv.exe pip install --python .venv\ocr\Scripts\python.exe -r services\ocr\requirements-model.txt` | Passed; isolated pinned CPU configuration |
| `.\.venv\ocr\Scripts\python.exe -m services.ocr.app.prepare` | Passed; first-run three upstream model downloads, about 16 MB; subsequent files verified by SHA-256 |
| `.\.venv\ocr\Scripts\python.exe -m services.ocr.verify_model` | Passed real CPU PNG and JPEG extraction, expected synthetic text, dimensions and boxes; not an accuracy benchmark |
| `.\.venv\test\Scripts\python.exe tests\e2e\generate_ingestion.py` | Passed; generated only synthetic inputs into ignored `.venv/ingestion-fixtures` |
| `node tests\e2e\ingestion_smoke.mjs` | Passed with local real CPU OCR + fixture gateway + Vite; OCR edit/submission, real local QR text/URL decoding, payment rejection, invalid/no-code failures, stale-review clearing, no external browser requests |
| `.\.venv\test\Scripts\python.exe scripts\smoke.py --base-url http://127.0.0.1:5173/api --expect fixture` | Passed; live/ready, complete fixture analysis, Demo data flag preserved |
| `git diff --check` | Passed after removing trailing blank lines |

Initial verification exposed a missing setuptools runtime dependency, an OCR
header fixture error, and a test-only TypeScript encoder argument; all were fixed
before the passing runs. A clean npm reinstall first failed because this task's
Vite process held a Windows native binding open. Stopping the task-started servers
released that lock, and the clean install/checks were rerun. Temporary services
were stopped after the smoke test. Sandbox pytest temp output was redirected to
`.venv/pytest-temp`; no system-directory write is required.

## Integration and limitations

Main still has unavailable live text/URL detectors. Existing gateway PR #18 and
text PR #19 are open; this branch does not import their unrelated changes. The
manual P0 fixture flow passes, but live P0 readiness is incomplete. Publish as a
**draft PR**, pending owner review and P0 integration, rather than asserting live
scam-detection end-to-end readiness. All fixture results remain Demo data and
aggregate `risk_score` remains null.

OCR English only; small/blurred/rotated/complex screenshots may require manual
correction or fail. No multilingual or detection-performance claim. CPU compatibility
was verified on Windows; Docker/Linux and paid live text inference were not tested.
Docker is not installed on this machine. Model-enabled container wiring requires
an explicit local model mount/build; default OCR Compose profile remains model-free.
Node 24.14.1 passes the actual checks but is below the existing jsdom transitive
dependencies' advertised 24.15 minimum; use a current Node 24 patch in CI.

Single QR codes containing readable text or HTTP(S) URLs are supported. Payment,
contact, Wi-Fi, app links and binary payloads are unsupported; recipients are not
verified. Browser image decoding happens before QR dimensions can be checked;
OCR's pixel limit is checked before full decode/inference. Inference may finish
after a gateway timeout, but results/images are never saved.

The schemas and root Compose/CI definitions are unchanged. `IngestionPanel`
reuses `App`'s existing analyze callback with `source=screenshot|qr`. Stephen's
review is needed for that proposed component boundary; Faisal's review is needed
for replacing the reserved extraction stub with private OCR forwarding. No prior
owner agreement is claimed. See component READMEs for setup and attribution.
