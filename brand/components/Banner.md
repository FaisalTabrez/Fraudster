# Banner

Mode and coverage notices. Blue describes the tool (checks that didn't run); striped yellow describes the data source (fixtures).

- **Demo** `.fr-banner--demo`: page-level and sticky at the top, full width, `role="status"`; stripes `demo-stripe-a`/`demo-stripe-b` at -45°, 10px bands (8px on mobile, 13px text: "**Demo data** · not live detection"); flask icon; `demo-fg`.
- **Partial** `.fr-banner--partial`: inside the result, directly under the ActionCard; `coverage-bg`, 1px `coverage-border`, `coverage-fg`, triangle icon. Name what didn't run and what the result is based on.
- **Unavailable** `.fr-banner--unavailable`: 2px `coverage-strong-border`, `coverage-strong-fg`, circle-slash icon. Always says "This is not a clean result."
- Lead with a bold two-word label ending in a full stop.
