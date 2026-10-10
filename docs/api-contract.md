# Fraudster API contract

## Public routes

- `POST /v1/analyze` accepts the frozen JSON request and returns the frozen analysis response.
- `POST /v1/extract` accepts one PNG/JPEG multipart `file`, forwarding to optional private OCR. All extraction results use the existing extraction response shape.
- `GET /health/live` reports a running process.
- `GET /health/ready` returns HTTP 200 in fixture mode and HTTP 503 in the scaffolded live mode.

The packaged browser calls these routes through the same-origin `/api` prefix. The prefix is deployment routing and is not part of the gateway route itself.

## Analyze request

`text` is optional and capped at 10,000 characters. `urls` contains at most five strings of at most 2,048 characters. `messages` contains at most 20 objects with unique request-local `id`, `sender_id`, text up to 2,000 characters, and an optional timestamp. `sender_id` identifies the protected user's sender ID when known. `conversation_id` is client correlation only, not authentication or proof of identity. `source` is one of `manual`, `screenshot`, `qr`, or `conversation`.

At least one nonempty input is required. Length limits apply to the raw submitted strings. Required message fields, URL strings, and supplied IDs must contain a non-whitespace character. Unknown fields are rejected. Validation and URL extraction do not dereference links.
Message IDs must be unique within a request; the gateway enforces this cross-item rule because JSON Schema cannot express uniqueness of one object property within an array.
Identifier values are opaque: the gateway preserves whitespace within and around nonblank `id`, `sender_id`, and `conversation_id` values. Sender grouping, protected-user exclusion, and evidence citations use those exact supplied values.

## Analyze response

`status` is `complete`, `partial`, or `unavailable`. Verdicts are `legitimate`, `spam`, `suspected_scam`, and `unknown`. Severity is `low`, `medium`, `high`, or `unknown`.

`risk_score` is null during bootstrap and `probability_calibrated` is false. Per-module scores may appear only with a named `raw_score_type`; fixture policy points and future URL heuristic values must not be relabeled as fraud probability.

Each evidence item has a stable ID, indicator type, source module, explanation, and at least one nonblank quote or actual observed value. Conversation evidence carries the exact source message ID. Both module-level and aggregate suspected-scam verdicts require evidence.
The gateway keeps detector evidence only when its nonblank quote or string observation occurs in the supplied input for that detector. An unsupported detector warning becomes `unknown`.

Coverage always includes text, URL, conversation, and reputation. Values are `complete`, `not_applicable`, `not_run`, or `unavailable`. Missing checks are never converted into zero risk.

`module_results` preserves detector version, status, raw score type, optional score, evidence, and a safe detail. It never includes provider secrets or raw internal stack traces. `fixture_generated` marks the whole response and each fixture detector result.

Applicable text and URL detector calls start concurrently and share the configured overall analysis deadline. A failed or timed-out detector is recorded as unavailable without discarding completed module results. If every applicable detector is unavailable, the aggregate status is `unavailable` and its verdict and severity are both `unknown`.

Conversation rules group messages by `sender_id`; evidence from different senders is never combined into one escalation. When the top-level `sender_id` is supplied, it identifies the protected user and those messages are excluded from escalation rules.

## Internal route

Text and URL services expose `POST /predict` plus health routes. The text predictor still returns HTTP 503 until its reviewed adapter is configured. The URL predictor uses the pinned string-only extractor, rules, and JSON model and returns the gateway `ModuleResult` shape; it never fetches the submitted URL. Its 0–100 blended policy score is not the aggregate `risk_score` or a calibrated fraud probability.

## Extraction boundary

The route accepts one multipart `file`, with a 5,000,000-byte image limit and a bounded 65,536-byte multipart envelope. Private OCR validates PNG/JPEG content and headers, enforces 20 million decoded pixels before decoding/inference, and returns editable text plus boxes and image dimensions. HTTP 413/415/422/503 responses use `status=unavailable`, null text, empty boxes, and explicit details; dimensions are included when known. Missing OCR does not prevent analysis. See `services/ocr/README.md` for optional English CPU model setup.

The machine-readable source of truth is in `contracts/`. Examples are illustrative contract fixtures, not live predictions.
