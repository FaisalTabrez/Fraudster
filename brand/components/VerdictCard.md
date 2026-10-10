# VerdictCard

The four verdicts, in human words over the API's categories. Each differs by icon shape and border style, never by hue alone.

| Verdict | API | Fill / border | Icon |
|---|---|---|---|
| Potential scam | `suspected_scam` · high | solid `scam-bg`, 1px `scam-border` | octagon (`verdict-scam`). Requires evidence. |
| Likely promotional | `spam` · low | `promo-bg`, 1px `promo-border` | tag (`verdict-promotional`) |
| No strong warning found | `legitimate` · low | `surface`, 1.5px `clear-border`, outline only | empty shield, no tick (`verdict-no-warning`): absence of warning, not proof of safety |
| Unable to assess | `unknown` · unknown | `unknown-bg`, 1.5px DASHED `unknown-border` | dashed circle + ? (`verdict-unable`). Never shown as safe. |

- Name 22/700 in the tone's fg; one-line advice 15px; a meta rule then the API enum in `mono`.
- Never say "safe", never show a tick or a green fill for a verdict.
