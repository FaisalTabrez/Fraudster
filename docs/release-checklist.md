# Release checklist

This checklist separates completed engineering gates from decisions or evidence that cannot be fabricated in code.

## Automated gates

- Node 24 typecheck, web tests, and production build.
- Python gateway, text, OCR, contract, integration, and URL 3.13 tests.
- Clean Docker Compose build and fixture smoke.
- Default live partial smoke for text plus URL, and unavailable smoke for text only.
- JSON contract, brand-token, and third-party-manifest parsing.
- Aggregate `risk_score` remains null; fixture output remains visibly marked.

## Human or configured-environment gates

- Curate and freeze at least 30 development and 20 untouched holdout scenarios without private message content.
- Record provenance, supporting evidence, two reviewers, at least six conversations, and at least five failure cases.
- Run `evaluation/run_evaluation.py --require-release-dataset` against configured live adapters; do not tune on the holdout.
- Run the optional PaddleOCR model verification and real synthetic-image browser smoke from `docs/ingestion-verification.md`.
- Record the actual clean-setup and three-minute demo outcomes; do not substitute fixture matches for accuracy.
- Choose and add a root project license. Third-party notices do not license the Fraudster repository itself.
- Confirm the configured text provider's data-handling terms match the UI disclosure before a public demo.
