# Architecture and scope decisions

## 2026 10 09 Empty repository bootstrap

The GitHub repository existed but had no commits or files. The requested layout was created on local branch `chore/bootstrap`; no existing application, branding, remote, or user change was replaced. Nothing was pushed or deployed.

## One gateway and no database

The React client calls a single public FastAPI gateway. Detector services are private. The gateway owns deadlines, coverage, conversation rules, and the warning policy. Conversation history is supplied in each request and is not stored.

## Honest default and explicit fixtures

Default mode returns unavailable/unknown until real adapters are installed. Fixture mode is an explicit environment choice, skips external calls, marks the response as fixture-generated, and displays Demo data in the UI. Fixture outputs support integration work only.

## SmishX adapter boundary

At inspected commit `116a8c827741e0572563f678d25ed04306b1e3ff`, the earlier findings still apply: the main interface combines phishing and spam as a boolean, final-detection failure returns `category: true`, and `_expand_url` runs for every extracted URL before optional URL checks. No source is copied. ZEE 01 and ZEE 02 must repair these behaviors behind a validated adapter using environment configuration and request-local output.

## URL adapter boundary

At inspected commit `8648994a2e2ff25eac8fe23b46705ecbcd27f296`, the project requires Python 3.13+, validates a 20-feature order against JSON model metadata, and combines model output with a 0-100 heuristic policy score. Its Safe/Suspicious/Dangerous bands are not guarantees and the blend is not assumed calibrated. The adapter gets a separate Python 3.13 service. No source, model, dataset, or pickle/joblib file is copied during bootstrap.

## Optional ingestion

PaddleOCR and `@zxing/browser` are P1 only. OCR must verify a small CPU model, download behavior, language coverage, and version compatibility. QR decoding stays in the browser, never opens decoded content, and makes no claim about recipient identity.

## Rejected runtime additions

The Spoorthy phishing API is excluded from P0 because the prior reviewed routes used all-zero GBC features. The Elif phishing framework is only a future training reference. Multiple competing URL detectors, model retraining, live call interception, unrelated-app access, accounts, payments, stored history, campaign graphs, Kubernetes, background jobs, and broad live webpage crawling are out of sprint.

## Toolchain

The web targets Node 24, which is an LTS release line, and pins the installed frontend packages in `package-lock.json`. Gateway/text use Python 3.11 containers; URL uses Python 3.13; OCR is an optional Python 3.11 shell. Each service owns its dependency manifest and image.
