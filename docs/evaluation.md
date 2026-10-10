# Evaluation method

## Bootstrap status

`evaluation/fixtures/scenarios.json` contains six explicitly authored synthetic examples for contract and UI checks. They are not the planned sprint development and holdout sets, and their fixture-mode matches must not be reported as detection accuracy.

## Sprint sets

Priya freezes 30 labeled development scenarios at H4 and a separate 20-case holdout by H24. Include legitimate OTP notifications, promotions, delivery updates, and job discussions alongside credential theft, fake offers, and payment pressure. Include at least six complete conversation threads and five service/input failures. Mark source versus synthetic provenance and record supporting evidence plus reviewer. Keep each conversation and near-duplicate template in one split. Two teammates review ambiguous labels. Do not tune on the holdout.

Each release scenario uses these machine-readable fields:

- `split`: `development` or `holdout` (`bootstrap` is reserved for synthetic contract examples).
- `case_kind`: `detection`, `conversation`, or `failure`.
- `provenance`: a non-secret source record or an explicit synthetic label; never paste a private conversation.
- `support`: the evidence supporting the expected label.
- `reviewers`: two distinct reviewer identifiers after disagreements are resolved.
- `expected_verdict`, plus `expected_status` or `expected_http_status` where a failure path is under test.

Release metadata sets `synthetic` to false, `holdout_frozen` to true, and `holdout_tuning_prohibited` to true only after those statements are accurate. Keep related threads and near-duplicates under the same split during curation.

## Measurements

For live adapters, report sample counts, scam precision and recall, benign false positives, per-category confusion, p50/p95 latency, errors, and partial responses. Record model, prompt, policy, and code versions. Separate fixture contract checks from live-model evaluation. Do not reuse upstream accuracy or call a score calibrated without a calibration study.

## Harness

`evaluation/run_evaluation.py` sends the selected scenarios to a running gateway, measures client-observed latency, and records expected-to-actual pairs, HTTP/result status, fixture state, version matrix, scam precision/recall, benign false positives, errors, and partial/unavailable counts. It prints results by default and writes a file only when `--output` is supplied. Review and commit only intentionally selected, non-sensitive result files.

Use `--require-release-dataset` for a release-evidence run. It exits nonzero unless all dataset gates are present and no fixture-generated response was measured. The six bootstrap scenarios deliberately fail that gate and therefore cannot be presented as detector accuracy.

## Required failure cases

- Text unavailable while URL completes.
- URL unavailable while a no-link text scam still has evidence.
- Both applicable detectors unavailable.
- Invalid model JSON and malformed public request.
- Overall deadline with a completed partial result preserved.
- Same indicators split across different senders.
- OCR unsupported format, oversize bytes, and excessive decoded pixels if P1 ships.
