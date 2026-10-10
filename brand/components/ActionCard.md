# ActionCard

The top of every result: what to do now, in the verdict's tone, before anything else.

- Order inside: eyebrow "What to do now" → the action as the headline (`action`, 32/700; `action-mobile` 26/700) → one supporting sentence (`lead`) → a rule, then the verdict icon + name and a meta line.
- Tones: `.fr-tone-scam` (solid `scam-bg`, 1px `scam-border`), `.fr-tone-unknown` (`unknown-bg`, 1.5px DASHED `unknown-border`, dashed rule). `.fr-tone-promo` and `.fr-tone-clear` exist for the other two verdicts; the template shows only scam and unable as action cards.
- The meta line always hedges: "2 warning signs found · Not a guarantee", "No checks completed".
- Unable carries a "Try again" secondary button on the right of the foot.
- Consumer provides: action headline, supporting line, verdict, count. Put the ActionCard first in an `aria-live="polite"` result region.
