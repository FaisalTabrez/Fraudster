# Fraudster Contributor Guide

This repository contains the hackathon bootstrap for the Fraudster scam-warning prototype. Keep the repository name and existing branding; `ScamShield` is only a working label used in planning.

## Safety and scope

- Never fetch, follow, or open user-submitted URLs during analysis.
- Never log raw message text, API keys, private conversations, or provider responses containing secrets.
- Missing checks are unknown or unavailable, never zero risk.
- Keep aggregate `risk_score` null until a documented aggregate policy exists.
- Fixture outputs must remain visibly marked as demo data and must not be reported as model performance.
- Do not add persistent message storage, accounts, payment handling, broad crawling, or background jobs in the bootstrap.

## Shared boundaries

- The public browser API is the gateway only. Browser code calls `/api`; text, URL, and OCR services remain private.
- Faisal owns changes under `contracts/` and root runtime wiring after consultation with affected owners.
- Each service keeps its own dependency manifest and Dockerfile.
- Preserve third-party notices and update `third_party/manifest.json` before copying upstream code or model assets.
- Do not commit `.env`, credentials, private examples, downloaded datasets, caches, or unreviewed serialized model files.

## Verification

Run the checks for the component you changed and include the exact command and outcome in the pull request. The baseline checks are documented in `README.md`. Keep `main` runnable and prefer short integration pull requests.
