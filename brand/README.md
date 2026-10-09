# Fraudster brand kit

Everything needed to build Fraudster screens that match the UI template.

| Folder / file | What's in it |
|---|---|
| `brand-guidelines.md` | Voice, colour, type, spacing, result order, URL rules, iconography, logo usage. Start here. |
| `logo/` | Mark and lockup (mark + wordmark), normal and reversed, as SVG; PNG exports. |
| `tokens.json` | Every colour, text style, spacing step, radius, shadow and control size, with usage notes. |
| `tokens.css` | The same tokens as CSS custom properties (`--brand`, `--space-16`, …), `@font-face` rules and a class per text style (`.action`, `.body`, `.label`, …). |
| `components/components.css` | Component classes (`.fr-btn`, `.fr-verdict`, `.fr-banner`, …) built on `tokens.css`. |
| `components/*.md` | Usage guide per component: what it's for, which tokens it uses, what the consumer provides. |
| `icons/` | The 17 stroke icons from the template (24×24 SVG, drawn in ink). |
| `fonts/` | Public Sans (variable, 400–700) and IBM Plex Mono 400/500, Latin subset, woff2. |
| `ui-template/` | The original Fraudster UI template (open in a browser). |

## Using it in a web page

```html
<link rel="stylesheet" href="brand/tokens.css">
<link rel="stylesheet" href="brand/components/components.css">
<body class="fr" style="background: var(--ground)">
  <button class="fr-btn fr-btn--primary">Check this message</button>
</body>
```

Light theme only. The template defines no dark theme yet.
