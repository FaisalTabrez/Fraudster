# ParticipantChip

Pill chips that label who is in a pasted conversation.

- Base `.fr-chip`: min-height `control-chip`, radius `radius-pill`, 14/600, `surface` with `line-strong` border.
- `--me`: `brand` fill, `on-brand` text. The user's own messages are never counted as warning signs.
- `--unknown`: `scam-bg`, `scam-border`, `scam-strong` text.
- `--add`: dashed `unknown-border`, `ink-2`, 400: "+ Add person".
- Names someone claimed go in curly quotes: “Bank support”. In forms the chips are `<button>`s (min-height 40px).
