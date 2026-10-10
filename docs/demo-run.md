# Recorded startup and demo run

What was actually run, on what, and what came out. Nothing here is a model-performance result: the fixture rows come from keyword rules and the live rows from the pinned URL adapter with no text provider key.

## Environment

- 10 October 2026, Windows 11 (build 26200), native processes, no Docker, no `.env` file, no `TEXT_API_KEY`.
- Python 3.14.8 in a fresh virtual environment from `services/gateway/requirements-dev.txt`. CI uses Python 3.11 (gateway) and 3.13 (URL); those versions were not available here, so the CI runs themselves are the first check on them.
- Commit base: `58ef346` (`main` after PR #20), plus the PRI-01/PRI-02 changes.

## What was not done

- **Docker startup.** Docker is not installed on this machine, so `docker compose up --build` was not run. The Compose path is unverified.
- **The browser demo.** Node is not installed here, so the web app was not started and the on-screen parts of the demo were not exercised: the Demo data badge, the evidence cards, and the visual states. Only the API calls behind steps 1 to 5 were replayed.
- **Step 6 (OCR and QR)** needs the browser, so it was not run.
- **The three-minute timing.** No one rehearsed or timed the demo. The millisecond columns below are API latency only.

## Native startup

Each service is started with `python -m uvicorn <module> --host 127.0.0.1 --port <port>` from the repository root with `PYTHONPATH` set to it. Every process was live within a few seconds. No model was downloaded and no key was needed.

## Run 1: fixture mode (`DEMO_MODE=true`, gateway only)

```text
python scripts/smoke.py --base-url http://127.0.0.1:8101 --expect fixture
  live=live ready_http=200 mode=fixture analysis_status=complete verdict=suspected_scam
  fixture_generated=true checks_passed=43 checks_failed=0        exit 0

python tests/e2e/demo_walkthrough.py --base-url http://127.0.0.1:8101 --mode fixture      exit 0, 5/5 steps
```

| Step | Result | Actual |
|---|---|---|
| 1. Legitimate OTP notice | PASS | complete / legitimate / low, text coverage complete, 1 evidence, `risk_score` null, demo data |
| 2. No-link OTP scam | PASS | complete / suspected_scam / high, 1 evidence quoted from the message |
| 3. `http://192.0.2.10/verify` | PASS | suspected_scam / high, evidence `ip_address_host` = `192.0.2.10` |
| 4a. Conversation, same sender | PASS | suspected_scam / high, evidence cites `m1` and `m2` |
| 4b. Second sender changed | PASS | unknown / unknown, 0 evidence: the rule does not join different senders |

The development set over HTTP against this gateway scored 27 of 30 and listed 3 as skipped (the failure scenarios that need in-process control), with 0 errors and 0 contract violations.

## Run 2: `DEMO_MODE=false`, detector services not running

The gateway was pointed at a closed port for both services.

```text
python scripts/smoke.py --base-url http://127.0.0.1:8102 --expect unavailable
  ready_http=503 mode=live analysis_status=unavailable verdict=unknown
  fixture_generated=false checks_passed=44 checks_failed=0       exit 0

python tests/e2e/demo_walkthrough.py --base-url http://127.0.0.1:8102 --mode unavailable   exit 0, 2/2 steps
```

| Step | Result | Actual |
|---|---|---|
| 5a. Text and link, detectors unavailable | PASS | unavailable / unknown / unknown, text and URL coverage unavailable, 0 evidence, `risk_score` null, not fixture data (about 2.1 s, the time Windows takes to refuse the two connections) |
| 5b. Conversation rules still run | PASS | suspected_scam / high from the local rules, conversation coverage complete |

## Run 3: gateway with the real text and URL services, no provider key

```text
text  /health/ready -> {"status":"not_configured","ready":false,...}
url   /health/ready -> {"status":"ready","ready":true,"upstream_commit":"8648994a2e2f..."}

python scripts/smoke.py --base-url http://127.0.0.1:8105 --expect live-no-key
  ready_http=503 mode=live analysis_status=partial verdict=suspected_scam
  fixture_generated=false checks_passed=45 checks_failed=0       exit 0
```

One request, "Your parcel is held. Pay the fee at http://198.51.100.24/pay": `partial` / `suspected_scam` / `high`, coverage text `unavailable`, URL `complete`, conversation `not_applicable`, reputation `not_run`, `risk_score` null, not fixture data. The URL evidence reports real observed values (`url_feature_has_ip_host` = 1, `url_feature_is_https` = 0, host digit count 10). Versions: `url: phishing-url-detector@8648994a2e2f`, `text: not_available`.

This is what the default Compose stack does without a key: text is honestly unavailable while the URL check runs. It means demo step 5 as written ("applicable detector coverage becomes unavailable") only holds if the URL service is down too.

## Automated checks

```text
python -m pytest -q services/gateway/tests services/text/tests services/ocr/tests tests/integration
  158 passed in 22.50s        (the existing 95 tests plus 63 new ones)
python -m pytest -q services/url/tests tests/integration
  113 passed in 24.13s        (includes the tests that drive the real URL service)
python evaluation/validate_fixtures.py                              exit 0 (sets valid, not frozen)
python evaluation/run_evaluation.py --in-process --set development --check-expectations
  30/30 scored, 0 skipped, 0 errors, 0 contract violations, 0 unmet expectations   exit 0
```

## Findings from the run

- **`/health/ready` never turns ready in live mode.** The gateway returns 503 with the reason "text and URL adapters are scaffolded but not installed" regardless of detector health. In Run 3 the URL service was ready and the gateway still reported 503. Both adapters now exist, and readiness should reflect them (the text adapter is legitimately not ready without a key). The Compose health checks use `/health/live`, so startup is not affected. The gateway belongs to Faisal; this was not changed here.
- `scripts/smoke.py` currently expects HTTP 503 from `/health/ready` for the `unavailable` and `live-no-key` expectations. If readiness is fixed to mean "every configured detector is healthy", those two checks need to change with it.
