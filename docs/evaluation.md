# Evaluation method

## Status

The 30-case development set and the 20-case holdout are written, structurally validated, and committed as **drafts**. They are not frozen. Nobody has reviewed the labels yet, so the freeze and the two-reviewer sign-off still have to happen (see [Freezing a set](#freezing-a-set)). Until then nothing measured on them may be reported as a result.

| File | Content |
| --- | --- |
| `evaluation/fixtures/development.json` | 30 scenarios (`DEV-01` to `DEV-30`). Tuning is allowed here. |
| `evaluation/fixtures/holdout.json` | 20 scenarios (`HO-01` to `HO-20`). Final measurement only; never tune on it. |
| `evaluation/fixtures/scenarios.json` | The six bootstrap contract examples. They are not a sprint set. |
| `evaluation/fixture_set.py` | Loads the sets and computes the canonical content hash used for freezing. |
| `evaluation/validate_fixtures.py` | Checks the structural rules below; records the freeze. |
| `evaluation/run_evaluation.py` | Sends a set to a gateway and reports counts, confusion, scam precision/recall, benign false positives, latency, errors, partial and unavailable responses. |

All scenarios are **synthetic and authored**, marked `provenance: synthetic_authored`. No real message, person, brand, domain or phone number appears: URLs use `.test`, `.example`, `.invalid` or the documentation IP ranges (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`). The drafts were written with an AI assistant for the ticket owner, and the file metadata says so.

## What the sets contain

| | Development | Holdout | Total |
| --- | --- | --- | --- |
| Scenarios | 30 | 20 | 50 |
| Benign notifications (OTP notice, appointment, card alert, statement, library, benign deep link) | 6 | 4 | 10 |
| Promotions | 3 | 3 | 6 |
| Delivery | 4 | 0 | 4 |
| Job content (legitimate and scam) | 3 | 2 | 5 |
| Credential, fake-offer and payment-pressure scams | 7 | 7 | 14 |
| Complete conversation threads | 4 | 2 | **6** |
| Failure and degraded-mode scenarios | 3 | 2 | **5** |

The ticket asks for "six conversations" and "five failures". They are counted across the two sets, and `validate_fixtures.py` enforces at least six and five in total. If the team reads the ticket as per set, add scenarios to the holdout (it has two conversations and two failures).

Each scenario carries `group` (the template or thread it belongs to), `category`, `expected_verdict`, `support` (why the label is right), `ambiguous`, and `reviewers`. The expected verdict is what a careful human reader would label from the supplied text alone. It is never copied from a detector's output. The `label_policy` in each file's metadata spells this out.

### Failure scenarios

Five scenarios describe degraded modes, each with an `expected` block:

| ID | Condition | Expected |
| --- | --- | --- |
| `DEV-28` | text unavailable, URL completes | `partial`, URL evidence kept |
| `DEV-29` | URL unavailable, message has no link | `complete`, text scam keeps its evidence, URL `not_applicable` |
| `DEV-30` | both applicable detectors unavailable | `unavailable`, `unknown`/`unknown`, never clean |
| `HO-19` | blank-only request | HTTP 422, not analysed |
| `HO-20` | text misses the overall deadline | `partial`, completed URL result preserved |

A scenario with a `condition` needs control of the detectors, so it only runs with `--in-process`. Against a running gateway it is listed as skipped, never faked. The other service failures (invalid detector JSON, detector errors, ungrounded warnings) are covered by `tests/integration/test_p0_acceptance.py`.

## Structural rules (checked by `validate_fixtures.py`)

- Exactly 30 development and 20 holdout scenarios; unique ids; every field present.
- All provenance is `synthetic_authored`; every URL host is reserved or documentation-only.
- At least one scenario in each of: benign notification, promotion, delivery, job, credential scam, fake offer, payment pressure; at least six conversations (2 to 20 messages, unique ids) and five failures; every verdict is expected at least once.
- No group, template or thread appears in both splits.
- No near-duplicate (word-set Jaccard of 0.6 or more) across splits, and near-duplicates inside a split share a group, so templates stay together.
- A set that claims `freeze.status: frozen` must have two distinct reviewers on every scenario, a resolution on every ambiguous one, and a `FREEZE.json` hash that matches its content.

Run it with `python evaluation/validate_fixtures.py`. CI runs it on every pull request. Exit 0 means the structure holds; it does not mean the labels are right.

## Freezing a set

This is the human step the drafts are waiting for.

1. Two teammates, neither of whom wrote the label, each read every scenario and add their handle to its `reviewers` list. They record disagreement in a pull request comment, not by editing a label silently.
2. The five scenarios flagged `ambiguous` need a discussion and a `resolution` note: `DEV-05` (account-change notice), `DEV-11` (loyalty reminder), `HO-08` (vague exclusive offer), `HO-13` (wrong-number opener), `HO-16` (punycode host). Reviewers may also flag others.
3. Once every scenario has two reviewers, run `python evaluation/validate_fixtures.py --freeze development` (and `holdout` by H24). It refuses unless both conditions hold, then writes `evaluation/fixtures/FREEZE.json` with the content hash.
4. Set `metadata.freeze.status` to `frozen` and `frozen_at` to the date in the file, and rerun the validator. From then on, any edit to a frozen set changes its hash and fails the check.

Do not tune on the holdout. `run_evaluation.py --set holdout` refuses to run without `--final-run`, and the report records the fixture hash and freeze status so an unfrozen or edited holdout is visible.

## Running it

Contract and degraded-mode check, with no services and no network:

```powershell
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe evaluation\run_evaluation.py --in-process --set development --check-expectations
```

Against a running gateway (the only mode whose numbers can describe a live system):

```powershell
.\.venv\Scripts\python.exe evaluation\run_evaluation.py --base-url http://127.0.0.1:4173/api --set development
# once, after the freeze:
.\.venv\Scripts\python.exe evaluation\run_evaluation.py --base-url http://127.0.0.1:4173/api --set holdout --final-run --output evaluation\results\holdout.json
```

It prints the report as JSON and a one-line summary on stderr, and writes a file only when `--output` is given. `--check-expectations` exits 1 on a contract violation (non-null `risk_score`, scam without evidence, unavailable result that is not unknown, wrong coverage fields) or an unmet failure-scenario expectation.

## Reading a report

`reportable_as_detection_performance` is `true` only when the run was against the live gateway, on a frozen set, with no fixture-generated output and nothing skipped. Otherwise it is `false` and `reasons_not_reportable` says why. A fixture or in-process run still prints verdict agreement and scam recall, because that is how the harness is checked. Those numbers describe the fixture rules, not a detector. For example, the in-process development run agrees on 21 of 30 verdicts and finds 8 of 15 scams, because the fixture rules only know a few keyword patterns. Do not quote them.

The report includes: sample counts; confusion overall and per category; scam precision and recall (positive is `suspected_scam`); benign scenarios flagged as scams; unknown, partial and unavailable counts; request errors; p50 and p95 latency with its basis (`in-process call` or `client-observed HTTP`); every distinct component version seen; and the content hash of the set.

For a live evaluation also record the model, prompt and policy versions (the report carries the versions the gateway returns), and keep these rules from the project:

- Do not reuse upstream accuracy, and do not call a score calibrated without a calibration study.
- Aggregate `risk_score` stays null, so nothing here measures it.
- Report ambiguous scenarios separately from the headline when comparing runs.
- Separate fixture contract checks from live-model evaluation in anything written down.

## Limitations

- Fifty synthetic scenarios cannot support a claim about real-world accuracy. They check behavior, coverage and failure handling.
- Labels reflect one drafter's judgement until two reviewers have signed off.
- The text detector needs a provider key. Without one, a live run reports text as unavailable, so a live text evaluation cannot be produced in CI.
- Latency from `--in-process` is a function call, not a network request.
