# Fraudster scam warning prototype

Fraudster is a runnable hackathon prototype for an explainable scam-warning flow. The interface accepts pasted text, URL strings, and conversation messages supplied by the user, sends them through one FastAPI gateway, and displays grounded evidence plus explicit coverage gaps. Optional screenshot OCR and local QR decoding provide editable review before analysis; configuration-dependent checks stay explicitly unavailable when missing.

The repository was empty at kickoff, so the requested layout was created directly without replacing an existing application or branding. `ScamShield` is not used as the repository or product name.

## Current runtime truth

- Fixture mode is deterministic and visibly marked **Demo data** in every response and result view.
- Default/live mode starts without paid credentials. Text requires a configured provider and otherwise remains `unavailable`; the URL service uses a pinned string-only model and returns input-dependent results.
- The local conversation rules are active in both modes. They only combine risk signals from the same supplied sender and cite exact message IDs.
- Aggregate `risk_score` is always null. The UI does not turn null into zero percent.
- Submitted URLs are parsed as strings only. This scaffold does not fetch or open them.
- Local QR decoding is installed and never opens decoded URLs. Optional English CPU OCR returns text, boxes, and dimensions when prepared; missing models/services remain explicitly unavailable. See [OCR setup](services/ocr/README.md) and [ingestion handoff](apps/web/src/features/ingestion/README.md).

## Architecture

The browser calls `/api` on the web origin. Vite proxies that path to the gateway during native development; Nginx does the same in the packaged Compose demo. The browser never receives the private service names.

```text
browser -> web /api -> gateway:8000 -> text:8000
                                  \-> url:8000
                                  \-> ocr:8000  optional P1 profile
```

There is no database. Conversation history exists only in the current browser form and each request body.

## Docker quick start

Requirements: Docker with Compose. Copy the placeholder environment file and choose the mode explicitly.

```powershell
Copy-Item .env.example .env
# For the deterministic UI/contract demo, set DEMO_MODE=true in .env.
docker compose up --build
```

Open `http://localhost:4173`. With the untouched example (`DEMO_MODE=false`) and no provider key, the text check is honestly unavailable while the URL check runs, so a request that has both comes back `partial`. To include the optional model-free OCR service (see its setup guide for model-enabled operation):

```powershell
docker compose --profile ocr up --build
```

Stop the stack with `docker compose down`. Compose exposes only the web service on host port 4173; gateway and detector names remain internal.

## Native development

The frontend targets Node 24 LTS and has a committed lock file. The gateway and text service target Python 3.11. The URL adapter is isolated on Python 3.13 because its pinned upstream metadata requires Python 3.13 or newer.

Create the Python environment from the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r services\gateway\requirements-dev.txt
$env:PYTHONPATH = (Get-Location).Path
$env:DEMO_MODE = "true"
.\.venv\Scripts\python.exe -m uvicorn services.gateway.app.main:app --reload --port 8000
```

In another terminal:

```powershell
Set-Location apps\web
npm ci
npm run dev
```

Open `http://localhost:5173`. Fixture mode does not require the private text or URL processes. To inspect their unavailable-state APIs natively, install their own requirements and start them on separate ports; set `TEXT_SERVICE_URL` and `URL_SERVICE_URL` for the gateway before starting it.

## Verification

From the repository root after the Python environment is active:

```powershell
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe -m pytest -q services\gateway\tests services\text\tests services\ocr\tests tests\integration
```

Run the URL adapter checks in Python 3.13:

```powershell
py -3.13 -m venv .venv-url
.\.venv-url\Scripts\python.exe -m pip install -r services\url\requirements-dev.txt
$env:PYTHONPATH = (Get-Location).Path
.\.venv-url\Scripts\python.exe -m pytest -q services\url\tests
```

Run frontend checks:

```powershell
Set-Location apps\web
npm ci
npm run typecheck
npm test
npm run build
```

Check the evaluation sets and run the contract and degraded-mode pass (no services, no network, no key):

```powershell
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe evaluation\validate_fixtures.py
.\.venv\Scripts\python.exe evaluation\run_evaluation.py --in-process --set development --check-expectations
```

Against a running stack (Docker or native), pick the expectation that matches how it was started: `fixture` for `DEMO_MODE=true`, `partial` for the default Compose stack (URL complete, unconfigured text unavailable), `live-no-key` for a looser live service check, or `unavailable` for a text-only request when text cannot run:

```powershell
py -3 scripts\smoke.py --base-url http://127.0.0.1:4173/api --expect fixture
py -3 scripts\smoke.py --base-url http://127.0.0.1:4173/api --expect partial
py -3 scripts\smoke.py --base-url http://127.0.0.1:4173/api --expect unavailable
py -3 tests\e2e\demo_walkthrough.py --base-url http://127.0.0.1:4173/api --mode fixture
py -3 evaluation\run_evaluation.py --base-url http://127.0.0.1:4173/api --set development
```

The integration tests start real native processes and run the smoke script against them, so a clean checkout is checked end to end with no key, no model download and no network. `docs/demo-run.md` records an actual run.

The evaluation sets are synthetic. The development and holdout sets are drafts until two teammates have reviewed the labels and the sets are frozen; see `docs/evaluation.md`. Nothing here is a benchmark or production-readiness claim.

The partial check uses text plus an inert documentation-range URL. The unavailable check submits text only. Neither command opens the URL.

## Environment variables

| Variable | Default or example | Purpose |
| --- | --- | --- |
| `TEXT_SERVICE_URL` | `http://text:8000` | Private gateway-to-text endpoint |
| `URL_SERVICE_URL` | `http://url:8000` | Private gateway-to-URL endpoint |
| `OCR_SERVICE_URL` | `http://ocr:8000` | Optional private OCR endpoint |
| `ANALYSIS_TIMEOUT_SECONDS` | `10` | Overall deadline; clients use a smaller derived timeout |
| `DEMO_MODE` | `false` | Enables labeled, deterministic fixture responses |
| `TEXT_MODEL` | `configure-me` | Future text-adapter model selection |
| `TEXT_API_KEY` | empty | Backend-only provider secret; never a `VITE_` variable |
| `WEB_PORT` | `4173` | Public Compose port |

## Team handoff

Work starts from this shared bootstrap baseline. The agreed branches are `feat/gateway`, `feat/url`, `feat/text`, `feat/web`, `feat/ingestion`, and `test/evaluation`. Ownership, tickets, integration gates, and the 24-hour scope cut are in `docs/`.

Main includes gateway protections (PR #21), text adapter/failure handling (PRs #19/#17), and the string-only URL adapter/evidence (PRs #25/#26). Text still needs provider configuration; paid live text inference and overall live readiness are not claimed by this ingestion PR.

OCR/QR ingestion uses the existing analysis contract. PNG/JPEG OCR limits are decimal 5 MB and 20 million pixels. Review text before submission; payment QR payloads are unsupported and no recipient is verified. The ingestion PR remains draft pending final owner review and verification of the configured live stack.

See `third_party/manifest.json` before copying any upstream source or model. Do not copy upstream accuracy into team results.
