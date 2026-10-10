# Recorded startup and demo run

What was actually run, on what, and what came out. Nothing here is a model-performance result: the fixture rows come from keyword rules and the live rows from the pinned URL adapter with no text provider key.

## Environment

- 10 October 2026, Windows, Docker Engine 29.8.1 and Docker Compose 5.5.1. No `.env` file and no `TEXT_API_KEY` were used.
- The Compose images used their pinned runtimes: Python 3.11 for gateway/text, Python 3.13 for URL, and Node 24 for the production web build. Host checks used Python 3.12.10; the focused URL suite was also checked with Python 3.13.
- Commit base: `d455e60` (`main` after PR #28), merged into the PRI-01/PRI-02 branch, plus the release-gate fixes at `a648d99`.

## Human-only work still required

- **Two independent label reviewers.** Automation cannot supply human agreement. Every scenario still needs two teammates who did not write its label, plus resolutions for the five ambiguous cases, before either set can be frozen.
- **A human-timed narrated rehearsal.** The complete browser flow below was exercised with an automated operator, but no person has yet delivered and timed the narration. Do not describe the three-minute rehearsal as complete until a person records it.
- **Live text-provider evidence.** No provider or license choice was supplied, so no key was configured and no live text-model result was produced.

## Docker startup

The production containers built with zero npm audit findings and all four required services became healthy:

```text
$env:DEMO_MODE='true'
docker compose -p fraudster_pr33 up --build --wait --wait-timeout 180
  text healthy; url healthy; gateway healthy; web listening on 127.0.0.1:4173     exit 0
```

No model was downloaded and no provider key was needed.

## Run 1: fixture mode (`DEMO_MODE=true`, composed services and browser)

```text
python scripts/smoke.py --expect fixture
  live=live ready_http=200 mode=fixture analysis_status=complete verdict=suspected_scam
  fixture_generated=true checks_passed=43 checks_failed=0        exit 0

python tests/e2e/demo_walkthrough.py --mode fixture      exit 0, 5/5 steps
```

| Step | Result | Actual |
|---|---|---|
| 1. Legitimate OTP notice | PASS | complete / legitimate / low, text coverage complete, 1 evidence, `risk_score` null, demo data |
| 2. No-link OTP scam | PASS | complete / suspected_scam / high, 1 evidence quoted from the message |
| 3. `http://192.0.2.10/verify` | PASS | suspected_scam / high, evidence `ip_address_host` = `192.0.2.10` |
| 4a. Conversation, same sender | PASS | suspected_scam / high, evidence cites `m1` and `m2` |
| 4b. Second sender changed | PASS | unknown / unknown, 0 evidence: the rule does not join different senders |

The development set over HTTP against this gateway scored 27 of 30 and listed 3 as skipped (the failure scenarios that need in-process control), with 0 errors and 0 contract violations.

### Browser verification

A headed Chromium session exercised the production web container. It showed the visible **Demo data · not live detection** badge, evidence quotes, coverage states and safety limits for the legitimate, scam, URL and conversation cases above. Changing `m2` from `sender-a` to `sender-b` removed the cross-message warning, as required.

The URL case used only the documentation address `http://192.0.2.10/verify`. The browser network log contained local static requests and `POST http://127.0.0.1:4173/api/v1/analyze`; it contained no request to `192.0.2.10`.

For step 6, the repository generator created a synthetic QR containing `https://example.test/qr`. The browser decoded it locally into the review field. Uploading did not submit anything; only the explicit **Analyze reviewed content** click added a local `/api/v1/analyze` request, and there was no request to `example.test`. This verifies the review-before-analysis and never-open-the-link boundaries. The OCR container was not enabled because no OCR model asset was supplied.

## Run 2: `DEMO_MODE=false`, detector services not running

The gateway was pointed at a closed port for both services.

```text
python scripts/smoke.py --expect unavailable
  ready_http=503 mode=live analysis_status=unavailable verdict=unknown
  fixture_generated=false checks_passed=44 checks_failed=0       exit 0

python tests/e2e/demo_walkthrough.py --mode unavailable   exit 0, 2/2 steps
```

| Step | Result | Actual |
|---|---|---|
| 5a. Text and link, detectors unavailable | PASS | unavailable / unknown / unknown, text and URL coverage unavailable, 0 evidence, `risk_score` null, not fixture data (about 4.1 s for both connection attempts) |
| 5b. Conversation rules still run | PASS | suspected_scam / high from the local rules, conversation coverage complete |

## Run 3: gateway with the real text and URL services, no provider key

```text
text  /health/ready -> {"status":"not_configured","ready":false,...}
url   /health/ready -> {"status":"ready","ready":true,"upstream_commit":"8648994a2e2f..."}

python scripts/smoke.py --expect live-no-key
  ready_http=503 mode=live analysis_status=partial verdict=suspected_scam
  fixture_generated=false checks_passed=45 checks_failed=0       exit 0
```

One request, "Your parcel is held. Pay the fee at http://198.51.100.24/pay": `partial` / `suspected_scam` / `high`, coverage text `unavailable`, URL `complete`, conversation `not_applicable`, reputation `not_run`, `risk_score` null, not fixture data. The URL evidence reports real observed values (`url_feature_has_ip_host` = 1, `url_feature_is_https` = 0, host digit count 10). Versions: `url: phishing-url-detector@8648994a2e2f`, `text: not_available`.

This is what the default Compose stack does without a key: text is honestly unavailable while the URL check runs. It means demo step 5 as written ("applicable detector coverage becomes unavailable") only holds if the URL service is down too.

## Automated checks

```text
python -m pytest -q services/gateway/tests services/text/tests services/ocr/tests tests/integration
  165 passed, 3 skipped in 12.91s
python -m pytest -q services/url/tests tests/integration
  123 passed in 18.26s        (Python 3.13; includes the tests that drive the real URL service)
cd apps/web && npm run typecheck && npm test && npm run build
  typecheck passed; 9 files / 150 tests passed; production build passed
python evaluation/validate_fixtures.py                              exit 0 (sets valid, not frozen)
python evaluation/run_evaluation.py --in-process --set development --check-expectations
  30/30 scored, 0 skipped, 0 errors, 0 contract violations, 0 unmet expectations   exit 0
```

## Findings from the run

- **`/health/ready` still reports the old scaffold reason in live mode.** The URL service was ready and the text service was honestly `not_configured`, so HTTP 503 was correct, but the gateway reason does not describe those real adapter states. The Compose health checks use `/health/live`, so startup is not affected. Readiness correction is tracked separately from PRI-01/PRI-02.
- The synthetic fixture sets are useful for contracts, degraded-mode behavior and demo repeatability only. The evaluator now makes synthetic provenance an unconditional reason that a run is not reportable as detection performance, even if every operational gate later passes.
