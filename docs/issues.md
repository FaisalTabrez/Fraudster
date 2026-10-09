# Sprint implementation tickets

Effort ranges are focused engineering time inside the hackathon window, not elapsed deadlines. Every ticket includes component checks and a short handoff note.

## FAI 01 Gateway and frozen contract

- Owner: Faisal
- Priority: P0
- Paths: `services/gateway/`, `contracts/`, `docs/api-contract.md`
- Depends on: bootstrap baseline
- Effort: 3 to 5 hours
- Acceptance: gateway calls applicable detector interfaces concurrently; request limits and examples match JSON schemas; one unavailable service yields a useful partial result; all unavailable applicable detectors yield unavailable/unknown; aggregate score remains null.

## FAI 02 Sender scoped context and policy

- Owner: Faisal
- Priority: P0
- Paths: `services/gateway/app/risk/`, `services/gateway/tests/`
- Depends on: FAI 01 and the message schema used by STE 02
- Effort: 2 to 4 hours
- Acceptance: escalation evidence cites exact supplied message IDs; signals from different senders are not combined; protected-user messages are excluded when `sender_id` is provided; positive scam output always has evidence.

## AKH 01 Real URL adapter

- Owner: Akhilesh
- Priority: P0
- Paths: `services/url/`, `third_party/manifest.json`, `third_party/licenses/`
- Depends on: FAI 01
- Effort: 4 to 7 hours
- Acceptance: pin commit `8648994a2e2ff25eac8fe23b46705ecbcd27f296`; copy the complete string-only extractor, rules, and JSON model with notices; validate exact feature order; load model once; use Python 3.13+; return actual input-dependent output without network fetches.

## AKH 02 URL evidence and edge cases

- Owner: Akhilesh
- Priority: P0
- Paths: `services/url/app/`, `services/url/tests/`, `evaluation/fixtures/`
- Depends on: AKH 01
- Effort: 3 to 5 hours
- Acceptance: evidence exposes actual observed features and names heuristic, model, and blended score types separately; benign deep links, missing schemes, IP hosts, punycode, shorteners, and malformed values are tested; the upstream Safe band is not worded as a guarantee.

## ZEE 01 Structured text adapter

- Owner: Zeeshan
- Priority: P0
- Paths: `services/text/`, `third_party/manifest.json`, `third_party/licenses/`
- Depends on: FAI 01
- Effort: 5 to 8 hours
- Acceptance: pin and attribute reviewed SmishX source; return legitimate, spam, suspected scam, or unknown; quotes match submitted text; validated structured output includes model/prompt versions; fast path does not expand or browse URLs; no shared output files.

## ZEE 02 Spam unknown and deadline repairs

- Owner: Zeeshan
- Priority: P0
- Paths: `services/text/app/`, `services/text/tests/`
- Depends on: ZEE 01
- Effort: 3 to 5 hours
- Acceptance: invalid provider JSON, API failure, missing credentials, and timeout produce unknown/unavailable rather than a positive category; legitimate OTP, promotion, and credential scam remain distinct; no boolean or model self-rating is fabricated into a probability.

## STE 01 Scan and result flow

- Owner: Stephen
- Priority: P0
- Paths: `apps/web/src/features/scan/`, `apps/web/src/features/results/`, `apps/web/src/api/`
- Depends on: FAI 01 response examples
- Effort: 4 to 6 hours
- Acceptance: production build succeeds; browser calls `/api`; category, severity, evidence, recommendation, and all coverage fields render accessibly; null aggregate score stays absent; fixture responses always show Demo data.

## STE 02 Conversation and partial state UI

- Owner: Stephen
- Priority: P0
- Paths: `apps/web/src/features/conversation/`, `apps/web/src/features/results/`
- Depends on: FAI 02 and STE 01
- Effort: 3 to 5 hours
- Acceptance: users can enter up to 20 sender-tagged messages; evidence message IDs are readable; partial and unavailable states are not styled as success; mobile layout remains usable; UI does not claim access to unseen conversations.

## LIK 01 Screenshot extraction and correction

- Owner: Likhitha
- Priority: P1 after P0 passes
- Paths: `services/ocr/`, `apps/web/src/features/ingestion/`, `contracts/extraction-response.schema.json`
- Depends on: integrated P0 and agreed interface with Stephen
- Effort: 5 to 8 hours
- Acceptance: verified CPU-capable PaddleOCR version/model and language coverage; PNG/JPEG only; 5 MB and 20-million-pixel limits; boxes include image dimensions; extraction failures are explicit; users edit text before analysis; OCR assets remain optional.

## LIK 02 Local QR decoding

- Owner: Likhitha
- Priority: P1 after P0 passes
- Paths: `apps/web/src/features/ingestion/`, frontend tests, `third_party/manifest.json`
- Depends on: STE 01 and ingestion interface
- Effort: 3 to 5 hours
- Acceptance: pin compatible `@zxing/browser` and peer dependency; decode uploaded images locally; route decoded text/URL through the existing analyze request; never open decoded content; never claim payment-recipient verification.

## PRI 01 Frozen scenarios and evaluation harness

- Owner: Priya
- Priority: P0
- Paths: `evaluation/fixtures/`, `evaluation/run_evaluation.py`, `docs/evaluation.md`
- Depends on: starts at kickoff; FAI 01 schema by H4
- Effort: 4 to 7 hours
- Acceptance: freeze 30 reviewed development scenarios at H4 and a separate 20-case holdout by H24; include benign notifications, promotions, delivery/job content, scams, six conversations, and five failures; label synthetic data; keep threads and near duplicates in one split; two reviewers resolve ambiguous labels.

## PRI 02 Integration CI and clean start demo

- Owner: Priya
- Priority: P0
- Paths: `tests/integration/`, `tests/e2e/`, `.github/workflows/ci.yml`, `scripts/smoke.py`
- Depends on: all P0 handoffs
- Effort: 5 to 8 hours across the sprint
- Acceptance: CI needs no paid key or large model download; typecheck/build, schemas, unavailable/fixture modes, timeout, malformed request, sender separation, and null score are covered; clean Docker or native startup and the three-minute demo are recorded with actual outcomes.
