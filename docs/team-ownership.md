# Team ownership and integration

## Shared baseline

Everyone branches from the same merged bootstrap. Keep `main` runnable, use short pull requests, and include the check command, actual outcome, setup note, and remaining limitation. Fixture behavior, unavailable-state scaffolding, and live inference must be identified separately.

## Owners

- Faisal - integration lead; gateway, contracts, conversation rules, risk policy, Compose, shared bootstrap, merge and release decisions. Branch `feat/gateway`.
- Akhilesh - URL adapter, real feature extraction, model loading, URL evidence, and component tests. Branch `feat/url`.
- Zeeshan - text adapter, structured evidence, category separation, deadlines, and API failure behavior. Branch `feat/text`.
- Stephen - scan/results/conversation UI, accessibility, responsive behavior, and frontend API consumption. Branch `feat/web`.
- Likhitha - optional OCR service and frontend ingestion, including user correction and local QR decoding. Branch `feat/ingestion`.
- Priya - scenario curation, automated integration/e2e checks, CI, measured results, clean-start validation, and demo evidence. Branch `test/evaluation`.

## Shared-file rules

Only Faisal changes the frozen contracts after consulting affected owners; types, examples, and fixtures change in the same pull request. Stephen and Likhitha agree the ingestion component boundary before editing shared frontend files. Priya owns the check definitions, but each component owner fixes their own failures. Faisal coordinates root runtime and Compose changes. Faisal and Priya review integration.

`CODEOWNERS` remains comment-only until exact GitHub handles are confirmed. This repository does not claim that branch protection or remote permissions are configured.

## First handoffs

- Faisal: merged bootstrap, request/response examples, and branch boundaries.
- Akhilesh: one real URL result showing actual ordered features, named score type, model version, and unavailable handling.
- Zeeshan: distinct structured results for a credential scam, legitimate OTP notice, and promotion.
- Stephen: runnable interface against frozen fixtures, including null-score and partial-state display.
- Likhitha: CPU OCR compatibility spike and agreed correction-screen interface; QR contents remain unopened.
- Priya: versioned synthetic scenarios, expected outcomes, clean-start instructions, and automated contract checks.
