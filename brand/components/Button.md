# Button

Brand-green actions in three weights: one primary per screen, secondary for additive steps, text for the way out.

- **Primary** `.fr-btn.fr-btn--primary` — `brand` fill, `on-brand` label, 16/600, radius `radius-12`, min-height `control-lg` (52px; 54px with radius 14 for the sticky mobile submit, add `.fr-btn--block`). One per screen: "Check this message", "Check this conversation".
- **Secondary** `.fr-btn--secondary` — `surface` fill, 1px `line-control` border, `brand` label 15/600, min-height `control-min`. Additive or recovery actions: "+ Add a link", "Add message", "Check something else", "Try again" (on the unable card, use `unknown-border` and `unknown-heading`).
- **Text** `.fr-btn--text` — underlined `brand` label, offset 3px: "Start a new check".
- **Icon** `.fr-btn--icon` — 44×44, `ink-2`; always an `aria-label` naming the target ("Remove link 192.0.2.10").

Consumer provides: the label (a verb phrase about the user's thing, sentence case) and `type`. Never use red or verdict colours on buttons.
