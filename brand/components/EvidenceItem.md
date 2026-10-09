# EvidenceItem

A numbered warning sign, tied to the exact words in the pasted text.

- Number badge 28px `radius-pill`, `scam-fg` fill, `on-brand` 14/700; the same number appears as a superscript `.fr-ref` after the highlighted phrase.
- Highlight risky text with `.fr-mark`: `scam-bg` fill, `ink` text, 2px `scam-mark` underline.
- Title `item-title` (17/600), explanation `body-sm` in `ink-2`, then tags: the human module name and the rule enum in `mono`.
- Show the 2–3 strongest items only, under "Why we're warning you". Conversation evidence always shows the message number and its exact ID as `mono` chips (radius `radius-6`, 1px `line-strong`): "Message 1 · c1".
