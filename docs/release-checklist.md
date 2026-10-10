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

- Complete two independent human label reviews of the committed 30-case development and 20-case holdout drafts, resolve every flagged ambiguity, and freeze each set with `evaluation/validate_fixtures.py --freeze <set>`.
- Confirm the freeze hashes with `evaluation/validate_fixtures.py --require-frozen`; the validator also enforces provenance, support, split isolation, at least six conversations, and at least five failure cases.
- Run `evaluation/run_evaluation.py --set development` against configured live adapters. Run the frozen holdout only once with `--set holdout --final-run`; never tune on it.
- Run the optional PaddleOCR model verification and real synthetic-image browser smoke from `docs/ingestion-verification.md`.
- Have a person time and record the three-minute narration. The automated Compose and browser evidence is recorded in `docs/demo-run.md`; do not substitute fixture matches for accuracy.
- Choose and add a root project license. Third-party notices do not license the Fraudster repository itself.
- Confirm the configured text provider's data-handling terms match the UI disclosure before a public demo.
