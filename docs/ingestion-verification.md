# Ingestion review follow-up (#9, #10, PR #22)

Initially rebased onto main `e0c04be` (gateway PR #21, text PRs #19/#17, URL PRs #25/#26), preserving its contract,
grounded-evidence and opaque-identity protections. Review update: 2026-10-10.
Verified Windows x64 build 26200, Python 3.11.17, Node 24.21.0/npm 11.11.0;
browser smoke used Playwright 1.58.2 / Chromium 145.

## Findings addressed

- Faisal/Priya — OCR contention: one nonblocking admission slot per OCR process,
  acquired before upload reading, decode or inference. No waiting queue; excess
  requests get fast contract-shaped 503 and Retry-After. Cancellation/timeout
  does not release capacity until the actual worker closes its image. Tests cover
  concurrent admission, rejected-body unread state, cancellation, timeout and
  recovery; gateway maps busy responses without exposing upstream details.
- Faisal/Priya — colon text: reject only an explicit unsupported scheme list;
  ordinary `Note:hello` and `Meeting:10am` remain text. Unit, component and real
  browser QR regressions verify explicit submission without links/fetch/navigation.
- Faisal/Priya — provenance: retain immutable source commits/tags and package
  hashes. Each model's exact upstream archive URL/release path, archive SHA-256,
  member-to-local-file mapping and nine extracted-file hashes are recorded in
  the runtime metadata and manifest. Preparation no longer trusts a mutable
  PaddleOCR lookup. Archive hashes are checked before member parsing/writing;
  tests reject changed archives, files and destinations.
- Faisal/Priya — OpenCV: one `opencv-python-headless==4.10.0.84` distribution.
  A verified installer builds temporary PaddleOCR/imgaug compatibility wheels
  with dependency metadata changes only; implementation bytes unchanged. It
  verifies upstream wheel SHA-256, deterministically rebuilds RECORD/build
  metadata, checks actual OpenCV distribution ownership, and runs pip check.
  Fresh isolated installation and real PNG/JPEG inference passed.
  Tested transitive dependency versions are constrained to prevent silent resolver drift.
- Priya — browser OCR pixels: local image dimensions checked before screenshot
  upload, with blob cleanup and a no-upload regression. Server header checks
  remain authoritative and precede full pixel decode.
- Priya — CI engine: Node pinned to 24.21.0, satisfying existing jsdom engines;
  the same checksum-verified Node patch was used locally without engine warnings.
- Rebase/ownership handoff: current main includes gateway, text and URL integrations. The
  previous PR #18 handoff claim is removed. Contracts/ and root Compose wiring
  have no ingestion diff. CI's only change is the specifically requested Node
  patch pin. Owner approval is still pending; review requests are not approvals.

## Exact commands and actual results

Commands ran from repository root unless noted. Temporary environments, models,
archives, compatibility wheels and synthetic inputs are not committed.

| Exact command | Actual outcome |
| --- | --- |
| `.\.venv\test\Scripts\python.exe -m pytest -q services\gateway\tests services\text\tests services\ocr\tests tests\integration --basetemp=.venv\pytest-latest-main --tb=short -p no:cacheprovider` | **95 passed** on latest rebased main |
| `.\.venv\url-review\Scripts\python.exe -m pytest -q services\url\tests --basetemp=.venv\pytest-url-review --tb=short -p no:cacheprovider` | **37 passed** on Python 3.13.16 |
| `npm.cmd ci` (apps/web, Node 24.21.0 first on PATH) | Passed; zero vulnerabilities; no engine warnings |
| `npm.cmd run typecheck` (apps/web) | Passed |
| `npm.cmd test` (apps/web) | **32 passed / 4 files** |
| `npm.cmd run build` (apps/web) | Passed; main ~234 kB, on-demand ZXing ~477 kB |
| `.\.venv\Scripts\uv.exe venv .venv\ocr-review --seed --python .venv\runtimes\cpython-3.11-windows-x86_64-none\python.exe` | Passed; fresh isolated runtime |
| `.\.venv\ocr-review\Scripts\python.exe services\ocr\install_model.py` | Passed; one headless OpenCV distribution; pip check clean |
| `.\.venv\ocr-review\Scripts\python.exe -m pip check` | No broken requirements |
| `$env:OCR_MODEL_DIR = (Join-Path (Get-Location) '.venv\review-models'); .\.venv\ocr-review\Scripts\python.exe -m services.ocr.app.prepare` | Passed first-run downloads from explicit recorded URLs; archive and nine file hashes verified |
| `.\.venv\ocr-review\Scripts\python.exe -m services.ocr.verify_model` | Passed real CPU synthetic PNG and JPEG inference with dimensions/boxes |
| `.\.venv\test\Scripts\python.exe tests\e2e\generate_ingestion.py` | Passed synthetic-only fixtures, including colon-text QR images |
| `.\.venv\node-review\node-v24.21.0-win-x64\node.exe tests\e2e\ingestion_smoke.mjs` | Passed actual OCR/edit/demo-analyze, local QR text/URL/colon decoding, explicit submission, payment rejection, invalid/no-code/stale-review failures, zero external requests |
| `.\.venv\test\Scripts\python.exe scripts\smoke.py --base-url http://127.0.0.1:5173/api --expect fixture` | Passed; Demo data preserved |
| `git diff --check` | Passed |

An initial follow-up pytest invocation reused a temp directory across execution
contexts and hit Windows permissions. A fresh workspace-local basetemp with the
cache provider disabled passed all tests. Main advanced during verification;
README/notice conflicts were resolved preserving merged URL/text work, and the
suite rerun against that main passed 95 tests. No application failure was hidden.
Synthetic checks establish compatibility and behavior, not model performance.
Task-started services are stopped after verification.

## Remaining limits and integration status

Main has the reviewed gateway, text adapters and string-only URL adapter/evidence.
Text requires provider configuration; paid live text and a configured live stack
were not exercised. PR #22 remains draft pending owner reapproval and configured
live-stack verification. All fixture outputs stay Demo data and aggregate risk_score stays
null. No upstream implementation/model binary or private message is committed.

English OCR only; errors require review/correction. Single QR codes supported;
unsupported structured schemes are never recipient-verification claims. Browser
image decode precedes local dimension discovery; server OCR limits headers before
full decode. One CPU worker may finish after caller timeout, but cannot admit
more OCR work until it completes, and never persists results/images.

Docker/Linux inference was unverified at the initial pass; the follow-up below
verifies it. Paid live text inference remains unverified. Model-enabled Compose
still requires explicit build/model mounts. Current main has no conflicts after integration; future main changes can require another
rebase and verification. No future-conflict guarantee or reviewer sign-off is
claimed. See component READMEs for setup and ownership boundaries.

## Approved-source follow-up and current-main integration

Both reviewers approved source head `f9517de`, while explicitly keeping the PR
draft pending live-stack verification. Main subsequently advanced to `ba58d91`
(merged frontend PR #23); it was merged into the ingestion branch without
conflicts. Frontend/API/scan/result hardening is preserved, with **113 web tests**
now passing. No other open issues are assigned to Likhitha beyond #9 and #10.

Docker Desktop is now available (engine 29.7.2, Compose 5.4.0, Linux x86_64/WSL2
kernel 5.15.167.4, glibc 2.41, Python 3.11.17). The isolated test project is
`fraudster-pr22-review`, public port 4174. Its ignored local override only mounts
the verified `.venv/review-models` read-only at `/service/models` and sets
`OCR_MODEL_DIR`; root Compose is unchanged.

The container test exposed Nginx's default 1 MB upload ceiling. The public API
proxy now permits exactly 5,000,000 + 65,536 bytes of multipart envelope, matching
the gateway, and streams uploads instead of buffering them to disk. The new
public-boundary regression passes a synthetic PNG padded to exactly 5 MB and
rejects one extra byte with a contract-shaped unavailable response.

| Exact follow-up command | Outcome |
| --- | --- |
| `.\.venv\test\Scripts\python.exe -m pytest -q services\gateway\tests services\text\tests services\ocr\tests tests\integration --basetemp=.venv\pytest-main-web-integration --tb=short -p no:cacheprovider` | 95 passed |
| `.\.venv\url-review\Scripts\python.exe -m pytest -q services\url\tests --basetemp=.venv\pytest-main-web-url --tb=short -p no:cacheprovider` | 37 passed |
| `npm.cmd run typecheck`; `npm.cmd test`; `npm.cmd run build` (apps/web, Node 24.21.0 first on PATH) | Passed; 113 tests / 6 files; production build passed |
| `docker compose -p fraudster-pr22-review --profile ocr build --build-arg INSTALL_OCR=true ocr` | Linux CPU image built; one OpenCV distribution and pip check passed |
| `docker compose -p fraudster-pr22-review build web gateway text url` | All images built; web rebuild after proxy fix also passed |
| `$env:WEB_PORT='4174'; $env:DEMO_MODE='true'; docker compose -p fraudster-pr22-review -f compose.yaml -f .venv/pr22-compose.yaml --profile ocr up -d --no-build --wait --wait-timeout 90 ocr web` | Stack healthy; OCR readiness confirmed |
| `docker run --rm --network none --mount type=bind,source=C:/Users/likhi/Fraud,target=/workspace,readonly --mount type=bind,source=C:/Users/likhi/Fraud/.venv/review-models,target=/models,readonly -w /workspace -e OCR_MODEL_DIR=/models fraudster-pr22-review-ocr python -m services.ocr.verify_model` | Non-root Linux PNG/JPEG CPU inference passed, dimensions/boxes present, no network available |
| `.\.venv\test\Scripts\python.exe tests\e2e\upload_limit_smoke.py --base-url http://127.0.0.1:4174/api` | Exactly 5 MB accepted, one byte over rejected with unavailable 413 |
| `$env:INGESTION_BASE_URL='http://127.0.0.1:4174'; $env:PLAYWRIGHT_BROWSERS_PATH="$PWD\.venv\browsers"; .\.venv\node-review\node-v24.21.0-win-x64\node.exe tests\e2e\ingestion_smoke.mjs` | Actual Linux OCR/edit/demo analysis + local QR browser flows passed; zero external requests |
| `.\.venv\test\Scripts\python.exe scripts\smoke.py --base-url http://127.0.0.1:4174/api --expect fixture` | Passed; fixture outputs visibly marked Demo data |
| `$env:WEB_PORT='4174'; $env:DEMO_MODE='false'; docker compose -p fraudster-pr22-review -f compose.yaml -f .venv/pr22-compose.yaml --profile ocr up -d --no-build --wait --wait-timeout 90 gateway web` followed by `.\.venv\test\Scripts\python.exe scripts\smoke.py --base-url http://127.0.0.1:4174/api --expect any` | Non-demo stack passed; readiness 503 with missing text provider, partial coverage, fixture_generated false, risk_score null |
| `docker compose -p fraudster-pr22-review exec -T ocr python -m pip check` | No broken requirements found |

The initial public-limit test failed at the original proxy with HTML 413; after
the fix it reached the gateway but returned 503 before OCR was started. With
verified OCR running, it passed fully. These failures exposed setup/boundary
conditions and were not reported as successful extraction.

Priya's nonblocking installer suggestion is documented: `--no-deps` alone leaves
GUI OpenCV requirements in upstream metadata and fails dependency validation;
temporary compatibility wheels keep metadata consistent with the single selected
runtime. A future public OCR deployment should also bound upload read time; the
current private OCR is only fed a fully buffered, bounded gateway upload.

While these checks ran, Akhilesh integrated main and merged PR #22 at `44a4f72`
on 2026-10-10. These proxy changes were not part of that merge and are a separate
follow-up based on current main `58ef346`, preserving the new branding work.
Issue #10 is implemented on main; #9 still needs this public-upload limit fix
merged. Earlier source approvals do not approve this new follow-up.

Configured paid text-provider verification remains unperformed in this session
(no TEXT_API_KEY/TEXT_MODEL available). Both fixture integration and non-demo
unavailable-text behavior were verified; missing text coverage stays unknown,
not safe. No configured-provider performance claim is made. The isolated test
containers and network were removed with `docker compose -p fraudster-pr22-review
-f compose.yaml -f .venv/pr22-compose.yaml --profile ocr down`.
