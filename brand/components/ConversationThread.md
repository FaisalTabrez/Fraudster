# ConversationThread

The pasted conversation, rebuilt as a numbered thread so evidence can point at a message.

- `<ol class="fr-thread">` on `ground`, radius `radius-12`. Each `.fr-msg` max 85% wide; the who-line is 12px `caption` with the name bold in `scam-strong` (others) or `brand` (Me), then "· Message N".
- Others: `surface` bubble, 1px `line`, radius 4/14/14/14. Me (`.fr-msg--me`): right-aligned, `brand-tint`, radius 14/4/14/14.
- Below it, a composer: "Next message from [chip ▾]", a 2-row TextField, "3 of 20 messages" and an "Add message" secondary button.
