# Glass layer

Opt-in glassmorphism for the Fraudster brand kit. Nothing changes until an element carries `.glass`.
Preview it in dev at `/?preview=glass`.

## Where to use it, and where not

Use it for shells, stat cards, tabs, inputs and popovers. Do not use it for the action card,
verdict, coverage banners or evidence: people act on those, so they stay flat, solid and high
contrast (`brand/brand-guidelines.md`: "Borders, not shadows", "verdict colours describe the message").

## Token map

Every colour is an existing brand token (`styles/tokens.css`) or a `color-mix()` of one. A test
fails if a hex or `rgb()` value is added to `glass.css`.

| Tier | Class | Fill (of `--surface`) | Backdrop | Use |
|---|---|---|---|---|
| 1 | `.glass--1` | `--glass-1-alpha` 58% | blur 14px, saturate 140% | subtle card, tab track |
| 2 | `.glass--2` | `--glass-2-alpha` 72% | blur 20px, saturate 160% | button, field, tab |
| 3 | `.glass--3` | `--glass-3-alpha` 86% | blur 30px, saturate 180% | modal, popover |

| Part | Built from |
|---|---|
| Fill | `--surface` |
| Edge | `--line-strong` at 65% |
| Rim (specular border) | gradient from `--surface` 92% to `--brand` 26%, drawn with a mask |
| Highlight | `--surface` 60%, follows the pointer via `--mx` / `--my` |
| Shadow | `--ink` 8% plus `--brand` 30 to 46% |
| Ambient glow (`.glass-stage`) | `--brand` (at most `--glass-glow-alpha`, 22%), `--brand-tint`, `--ground` |
| Focus ring | `--brand`, 2px |
| Text | `--ink`, `--ink-2`, `--caption`, `--eyebrow`, `--brand`, `--on-brand` |

## Contrast

`glass.contrast.test.ts` composites each tier over the worst backdrop (the strongest brand glow)
and asserts WCAG AA: `--ink` at least 7:1, `--ink-2`, `--caption`, `--eyebrow` and `--brand` at
least 4.5:1, `--on-brand` on the primary button at least 4.5:1, focus ring at least 3:1. Making a
tier more transparent, or the glow stronger, fails the test.

## Fallbacks

Each swaps translucency for the plain solid token, so contrast only goes up:

- no `backdrop-filter`: `@supports not (...)` gives solid `--surface` and `--brand`
- no `color-mix()`: solid tokens, flat tint for the stage
- `prefers-reduced-transparency` or `prefers-contrast: more`: solid surfaces, no highlight
- `forced-colors: active`: system colours, no effects
- `prefers-reduced-motion`: no transitions or lift

## Components

`GlassStatCard`, `GlassButton` (`glass` or `primary`), `GlassTabs` (ARIA tabs with arrow, Home and
End keys), `GlassField` (label, hint and error wired with `aria-describedby`), and `useSpecular`
for the pointer highlight.
