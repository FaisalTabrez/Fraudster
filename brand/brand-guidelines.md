# Fraudster brand guidelines

Fraudster is a personal safety assistant that checks a message, link or conversation before someone acts on it. The interface is **calm, evidence-led, and honest about gaps**: a safety assistant first, with technical module detail one click away.

## Content fundamentals

- **Lead with what to do.** Every result opens with the action as a headline: "Pause. Don't reply, pay, or share codes yet." Then the verdict, then the evidence.
- **Human words over formal categories.** Say "Potential scam", "Likely promotional", "No strong warning found", "Unable to assess" — never the API enums (`suspected_scam`, `spam`, `legitimate`, `unknown`) except in `mono` meta lines and Technical details.
- **Never claim safety.** There is no "safe" verdict. Hedge every result: "Not a guarantee", "Still verify anything you didn't expect", "This is not a clean result."
- **Be honest about gaps.** Name what didn't run and what the result is based on: "1 of 2 checks couldn't run: link structure. The result below is based only on what did run."
- **Second person, plain, short.** "We" is Fraudster, "you" is the person. Sentence case everywhere; headings are questions or plain statements ("What did you receive?", "Why we're warning you", "What we checked", "Limits of this result").
- **Explain the privacy model in place.** "Only what you paste here is checked. Fraudster can't see your other chats or apps, and nothing is stored." "Links are read as text and never opened."
- No emoji, no exclamation marks, no urgency language (that is the scammer's voice).

## Colour

- Neutrals carry the page: `ground` page, `surface` cards and inputs, `sunken` tracks, chips and tags, `line` hairlines. Text is `ink`, `ink-2` for supporting copy, `caption` for counters and meta, `eyebrow` for uppercase labels.
- `brand` (deep green) is for action and identity only: primary buttons, links, the logo, the active participant, selected options and progress. Text on it is `on-brand`.
- **Verdict colours describe the message**: `scam-*` (red-brown), `promo-*` (amber), `clear-*` (green, outline only), `unknown-*` (slate, dashed). Each family has fg, bg, border plus text tints for headings, body and meta on its own fill — use those, not `ink`, inside a verdict surface.
- **Blue describes the tool**: `coverage-*` is only for checks that didn't run (partial and unavailable banners, the unavailable coverage row).
- **Striped yellow describes the data source**: `demo-stripe-a`/`demo-stripe-b` with `demo-fg` mark fixture data, nothing else.
- **Never by hue alone.** Every verdict also differs by icon shape and border style: scam = solid tint + octagon; promotional = soft tint + tag; no warning = white fill + outline + empty shield (no tick); unable = dashed border + dashed circle. Unknown is never shown as safe.
- All text pairs meet 4.5:1. The source's control borders (`line-strong`, `line-control`) and the dashed `unknown-border` are below 3:1; they are kept exact, and the fill, label or dash pattern carries the meaning.

## Type

- **Public Sans** (`sans`) for everything people read; **IBM Plex Mono** (`mono`) only for literal values: URLs, message IDs, API enums, versions, analysis IDs.
- The recommended action is the largest text on a result: `action` (32/700) on desktop, `action-mobile` (26/700) on mobile. Card headings `heading` / `heading-mobile`; body `body`; supporting `body-sm` and `small`; counters `caption`; eyebrows `label` (12/700, uppercase, 0.08em).
- Headlines tighten tracking (-0.02em to -0.005em); body text never does.

## Space, shape, depth

- Desktop: content max 1280px, side padding `space-32`, form and result columns side by side with `space-28` between (form 1 : result 1.5). Cards pad `space-28`; the result stack gaps `space-20`.
- Mobile (390px): side padding `space-16`–`space-20`, one step per screen, a sticky bottom submit on `ground` with a `line` top rule.
- Radii: `radius-16` cards, `radius-12` buttons/inputs/banners, `radius-10` inline panels, `radius-pill` chips and tags.
- Borders, not shadows. The only shadow is `shadow-segment` on the active segment.
- Touch targets are at least `control-min` (44px); primary submit is `control-lg` (52px).
- Keyboard focus: a 2px solid `brand` outline, offset 2px (8.5:1 on `ground`).

## Result order

Always, top to bottom: 1 ActionCard (what to do now) → 2 Verdict + coverage Banner → 3 the 2–3 strongest EvidenceItems → 4 CoverageList ("What we checked") → 5 Limits of this result → 6 TechnicalDetails (collapsed). The page-level demo Banner is sticky above everything while results come from fixtures.

## URLs are inert text

Show URLs with InertUrl: a plain `mono` span on `sunken`, host in `ink`, scheme and path dimmed to `caption`, a "Not opened" badge. Never an `<a href>`, never blue or underlined, no pointer cursor or hover colour, never copy-on-click without a label.

## Iconography

- 24×24 stroke icons, `fill="none"`, stroke 2 (2.2 for coverage statuses), round caps/joins — drawn for this template, stored in the Icons group. Inline them with `stroke="currentColor"` so they take the colour of their label; the stored files are drawn in `ink` (#1C211F).
- Sizes: 28px in verdict cards, 22px in action-card verdicts and mobile option wells, 20px in banners and notes, 18px in coverage statuses, 14px in badges.
- No emoji, no illustrations, no tick on any verdict.

## Logo

- The mark is a speech bubble holding a pause sign, in a `brand` rounded square (radius 16 on a 56 grid): "pause before you reply", the first thing every result tells people. Bubble and bars are `ground` and `brand`.
- Files (Logos group): `fraudster-mark.svg` (app icon, favicon, avatar), `fraudster-lockup.svg` (mark + wordmark, for headers), and `-reversed` versions for `brand` or `ink` grounds. PNGs for places that need bitmaps.
- The wordmark is Public Sans 700, -0.01em, in `ink` (outlined in the lockup files). In live UI, set it as text in `wordmark` beside the mark.
- Clear space: half the mark's height on every side. Minimum size: 20px mark, 96px-wide lockup.
- Don't recolour the mark into verdict colours, add a tick or shield, rotate it, or put the normal mark on `brand` (use reversed).

## Intentional additions

- The keyboard focus style above is not in the template; it was added so every control has a visible focus state.
- The logo was designed after the template, which only had a typographic "F" placeholder.
