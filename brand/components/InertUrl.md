# InertUrl

Shows a URL as inert text: Fraudster never opens links, and its UI must not invite a click.

- A plain `<span>` in `mono` on `sunken` with a 1px `line` border and radius `radius-10`. The host is in `ink`; the scheme and path are dimmed to `caption`.
- No `<a href>`, no underline, no pointer cursor, no hover colour, never blue. No copy-on-click without a label.
- In results, add the "Not opened" badge (eye-off icon, 12/600 `ink-2` on `surface`). In the input form, a remove icon button replaces the badge.
- A flagged host inside a quote is wrapped in the Evidence `.fr-mark` highlight.
