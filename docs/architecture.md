# Fraudster bootstrap architecture

## Decision

Fraudster uses one public FastAPI gateway between the browser and private detector services. This keeps request validation, deadlines, coverage semantics, conversation rules, and warning policy in one place while allowing incompatible Python runtimes to remain isolated.

```text
React TypeScript web
       |
       | same-origin /api
       v
FastAPI gateway
  |        |          |
  |        |          +-- optional OCR service under Compose profile
  |        +------------- URL service on Python 3.13+
  +---------------------- text service on Python 3.11
```

## Runtime boundaries

- Web: Node 24 LTS, React, TypeScript, and Vite. Development proxy and packaged Nginx both remove the `/api` prefix before forwarding.
- Gateway: Python 3.11. It validates the public contract, extracts URL strings without dereferencing them, calls applicable services concurrently, and keeps completed results when another call times out.
- Text: Python 3.11. The process is live without credentials, but readiness and prediction remain unavailable until the SmishX adapter is repaired and configured.
- URL: Python 3.13. The inspected upstream declares Python 3.13+, so it does not share the gateway environment.
- OCR: optional Python 3.11 service. It is excluded from the default dependency graph; explicit setup prepares verified English CPU models. Missing dependencies/assets keep extraction unavailable without preventing startup. Browser multipart uploads enter through gateway `/v1/extract`; only private OCR performs image validation/inference.

## Data flow

The client sends no hidden state. Each request contains current text, up to five URL strings, and up to 20 visible historical messages. The gateway deduplicates submitted and text-extracted URL strings while preserving the first display value. It does not fetch them.

Conversation rules group supplied messages by sender. A warning can combine urgency and a secret/payment request only when the same non-user sender supplied both. Evidence includes the original message IDs. No account, device, contact, reputation, or unseen history is inferred.

## Availability policy

Liveness means the process can answer. Readiness means the configured mode can produce the promised detector behavior. In live mode the gateway is ready only when every private detector reports ready (for example, the text adapter stays not ready until `TEXT_API_KEY` is configured). The Compose health chain uses liveness so the interface remains available to explain missing detection.

Applicable modules run under a ten-second overall default deadline and smaller per-service timeouts. A completed module survives another module's timeout. One missing applicable module makes the response partial; all applicable detector modules unavailable makes it unavailable with unknown verdict and severity. Reputation is not run in the bootstrap.

## Security and privacy boundaries

- No arbitrary URL fetches, redirect expansion, DNS lookup, WHOIS query, or broad webpage crawl in P0.
- No raw request messages, provider secrets, or stack traces in logs or responses.
- No API keys in frontend variables.
- No database or history persistence.
- Fixture mode never calls external detectors and is marked in the response and UI.
- QR decoding is local. Uploaded images become temporary blob images; decoded text/URLs are reviewed before explicit submission to the existing analyze route. Decoded URLs are never opened or fetched, and payment recipients are never verified.
