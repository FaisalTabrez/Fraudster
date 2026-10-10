# SegmentedControl

Picks the input type (Message / Link / Conversation) on desktop.

- Track `sunken`, padding and gap `space-4`, radius `radius-12`. Segments min-height `control-min`, radius `radius-9`.
- Active: `surface` fill, `ink` 600, `shadow-segment` (the only shadow in the system). Inactive: transparent, `ink-2` 500.
- Use `role="group"` with an `aria-label` and `aria-pressed` on each button. Add `.fr-seg--fill` to stretch segments across a form card.
- On mobile use InputOption tiles instead.
