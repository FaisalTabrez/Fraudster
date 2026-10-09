# Forty eight hour hackathon sprint plan

## Goal and working pace

Deliver a working manual text and URL flow, one bounded conversation-escalation demonstration, grounded evidence, explicit outages, and a reproducible API-backed frontend. Plan approximately 10 to 14 productive hours per contributor within the 48-hour window. Schedule sleep and handoff windows around the checkpoints; this is not a 48-hour continuous-work plan.

## H0 to H4 bootstrap and freeze

Faisal merges the additive scaffold, contract, examples, Compose wiring, and ownership boundaries. Priya begins scenario review. Akhilesh and Zeeshan audit their pinned upstream inference paths. Stephen works from response examples. Likhitha checks OCR/QR compatibility without changing the P0 startup path.

Decision gate: every owner can branch from one runnable baseline, and contract fixtures validate.

## H4 to H12 component handoffs

Akhilesh implements real URL feature/model loading and three bounded cases. Zeeshan implements structured text output for a scam, legitimate OTP notification, and promotion. Stephen completes the fixture-backed scan/results flow. Faisal holds contract and gateway integration office hours. Each contributor schedules a protected rest block after their handoff.

Decision gate: real inference is visibly distinct from fixtures, and both detector services return valid module results or honest unavailable states.

## H12 to H24 first integrated P0 flow

Connect frontend to gateway to text and URL services. Add the sender-scoped conversation demonstration and enforce the overall deadline. Priya adds integration cases for benign content, no-link scam content, invalid inputs, outages, and sender separation. Integrate in short pull requests rather than a final all-hands merge.

Decision gate: text, URL, conversation, evidence, and failure states work through one public origin.

## H24 to H36 hardening and conditional P1

Finish evidence grounding, benign deep-link cases, null-score display, partial results, and clean setup. Start screenshot/QR implementation only if the integrated P0 checks pass. Otherwise, Likhitha supports input, responsive, and failure-state work. Place another protected sleep/rest block before feature freeze.

Decision gate: P0 is stable. Unresolved OCR setup stays explicitly unavailable.

## H36 to H42 feature freeze and measurement

Freeze features. Priya runs the reviewed development and holdout sets, records sample counts, category confusion, scam precision/recall, benign false positives, latency, errors, and partial responses. Owners fix defects in their components. Fixture results are reported only as contract/UI checks.

## H42 to H48 release handoff

Faisal selects the final working commit. Priya repeats clean startup and the recorded demo. Each owner contributes setup, attribution, and limitations. Rehearse a three-minute demonstration and preserve the report, evaluation outputs, screenshots, and backup recording. Tagging or pushing requires a separate team decision.

## Twenty four hour fallback

Cut P1 completely. H0-H3 covers scaffold and schema; H3-H10 covers adapters and fixture UI; H10-H16 covers integration; H16-H20 covers verification; H20-H24 covers fixes and rehearsal. Deliver manual text/URL checking plus one sender-bounded conversation example and a small, clearly scoped evaluation.

## Scope cuts

1. If OCR is unresolved by H24, keep it unavailable and support text paste.
2. If P0 is incomplete by H30, remove QR/screenshot polish, history storage ideas, and additional languages.
3. If the text provider is unavailable, show text semantics as unavailable and keep URL analysis plus clearly labeled local rules.
4. At H36, remove incomplete screens and claims instead of extending scope.
