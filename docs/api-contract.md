# Fraudster API contract

## Public routes

- `POST /v1/analyze` accepts the frozen JSON request and returns the frozen analysis response.
- `POST /v1/extract` is reserved for PNG/JPEG screenshot extraction and currently returns HTTP 503 with the extraction response shape.
- `GET /health/live` reports a running process.
- `GET /health/ready` returns HTTP 200 in fixture mode and HTTP 503 in the scaffolded live mode.

The packaged browser calls these routes through the same-origin `/api` prefix. The prefix is deployment routing and is not part of the gateway route itself.

## Analyze request

`text` is optional and capped at 10,000 characters. `urls` contains at most five strings of at most 2,048 characters. `messages` contains at most 20 objects with unique request-local `id`, `sender_id`, text up to 2,000 characters, and an optional timestamp. `sender_id` identifies the protected user's sender ID when known. `conversation_id` is client correlation only, not authentication or proof of identity. `source` is one of `manual`, `screenshot`, `qr`, or `conversation`.

At least one nonempty input is required. Unknown fields are rejected. Validation and URL extraction do not dereference links.

## Analyze response

`status` is `complete`, `partial`, or `unavailable`. Verdicts are `legitimate`, `spam`, `suspected_scam`, and `unknown`. Severity is `low`, `medium`, `high`, or `unknown`.

`risk_score` is null during bootstrap and `probability_calibrated` is false. Per-module scores may appear only with a named `raw_score_type`; fixture policy points and future URL heuristic values must not be relabeled as fraud probability.

Each evidence item has a stable ID, indicator type, source module, explanation, and either a quote or actual observed value when available. Conversation evidence carries the source message ID. A suspected-scam verdict must have evidence.

Coverage always includes text, URL, conversation, and reputation. Values are `complete`, `not_applicable`, `not_run`, or `unavailable`. Missing checks are never converted into zero risk.

`module_results` preserves detector version, status, raw score type, optional score, evidence, and a safe detail. It never includes provider secrets or raw internal stack traces. `fixture_generated` marks the whole response and each fixture detector result.

## Internal route

Text and URL services expose `POST /predict` plus health routes. Their current predictor returns HTTP 503 because the reviewed upstream adapters are not copied or configured. Future adapters must return the gateway `ModuleResult` shape.

## Extraction boundary

The P1 route will accept multipart PNG/JPEG input, reject unsupported formats, enforce 5 MB and 20 million decoded pixels, and return editable text plus coordinate boxes and image dimensions. Until those checks and a verified CPU model exist, the route remains unavailable.

The machine-readable source of truth is in `contracts/`. Examples are illustrative contract fixtures, not live predictions.
