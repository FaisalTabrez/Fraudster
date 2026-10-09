# Fraudster brand kit

Static design assets for building Fraudster screens: guidelines, design tokens, component CSS, logos and icons. The kit contains no scripts and no font files.

| Folder / file | What's in it |
|---|---|
| `brand-guidelines.md` | Voice, colour, type, spacing, result order, URL rules, iconography, logo usage. Start here. |
| `logo/` | Mark and lockup (mark + wordmark), normal and reversed, as SVG; PNG exports. |
| `tokens.json` | Every colour, text style, spacing step, radius, shadow and control size, with usage notes. |
| `tokens.css` | The same tokens as CSS custom properties (`--brand`, `--space-16`, …) and a class per text style (`.action`, `.body`, `.label`, …). No `@font-face` rules; see Fonts below. |
| `components/components.css` | Component classes (`.fr-btn`, `.fr-verdict`, `.fr-banner`, …) built on `tokens.css`. |
| `components/*.md` | Usage guide per component: what it's for, which tokens it uses, what the consumer provides. |
| `icons/` | The 17 stroke icons from the original UI design (24×24 SVG, drawn in ink). |

## Fonts

The brand typefaces are Public Sans (400–700) for text and IBM Plex Mono (400, 500) for literal values such as URLs, message IDs and API enums. Both are SIL Open Font License fonts. They are not bundled here: load them from their upstream releases when the web app adopts the kit. Until then `--font-sans` and `--font-mono` fall back to system fonts.

The original generated UI template (a bundled HTML page) is deliberately not part of this kit. It can be added back in a later change together with its source, build steps, hashes and full third-party notices.

## Using it in a web page

```html
<link rel="stylesheet" href="brand/tokens.css">
<link rel="stylesheet" href="brand/components/components.css">
<body class="fr" style="background: var(--ground)">
  <button class="fr-btn fr-btn--primary">Check this message</button>
</body>
```

Light theme only. The original design defines no dark theme yet.
