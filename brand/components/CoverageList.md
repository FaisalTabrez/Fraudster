# CoverageList

"What we checked": one row per detection module, so people see what did and didn't run.

- In a Card with heading `heading` and a right-aligned count in `caption` ("2 of 2 applicable checks ran"; mobile "2 of 2 ran").
- Rows min-height 60px (56 on mobile), divider `sunken`. Name 600; note 13px `caption`.
- Statuses: **Checked** `clear-fg` 600 (circle-check); **Unavailable** `coverage-fg` 700 (triangle) and the whole row tinted `coverage-bg`; **Not applicable** `caption` (dash); **Not run** `caption` (dashed circle).
- Module keys map to human names: text → Message wording, url → Link structure, conversation → Conversation pattern, reputation → Sender reputation.
