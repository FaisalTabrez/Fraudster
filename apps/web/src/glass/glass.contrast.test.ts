import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// Read as plain text: Vitest does not return the source for CSS imports.
const read = (relative: string): string => readFileSync(new URL(relative, import.meta.url), "utf8");
const glass = read("./glass.css");
const tokens = read("../styles/tokens.css");

// WCAG 2.x contrast of text over translucent glass. The backdrop behind a glass surface is not a
// single colour, so each check uses the WORST backdrop the ambient stage can put behind it:
// the strongest brand glow for dark text, plain white for light text.

const token = (name: string): string => {
  const match = new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`).exec(tokens);
  if (!match) throw new Error(`token --${name} not found in tokens.css`);
  return match[1];
};
const percent = (name: string): number => {
  const match = new RegExp(`--${name}:\\s*(\\d+)%`).exec(glass);
  if (!match) throw new Error(`--${name} not found in glass.css`);
  return Number(match[1]) / 100;
};

type Rgb = [number, number, number];
const rgb = (hex: string): Rgb => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as Rgb;
// foreground at `alpha` over background, as the browser composites it
const over = (fg: Rgb, alpha: number, bg: Rgb): Rgb => fg.map((c, i) => c * alpha + bg[i] * (1 - alpha)) as Rgb;
const luminance = ([r, g, b]: Rgb): number => {
  const [lr, lg, lb] = [r, g, b].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
};
const ratio = (a: Rgb, b: Rgb): number => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

const ground = rgb(token("ground"));
const surface = rgb(token("surface"));
const brand = rgb(token("brand"));
const glow = over(brand, percent("glass-glow-alpha"), ground); // darkest backdrop dark text can meet
const tiers = { "tier 1": percent("glass-1-alpha"), "tier 2": percent("glass-2-alpha"), "tier 3": percent("glass-3-alpha") };

describe("glass contrast (WCAG AA)", () => {
  for (const [name, alpha] of Object.entries(tiers)) {
    const fill = over(surface, alpha, glow);

    it(`${name}: --ink body text is at least 7:1 on the worst backdrop`, () => {
      expect(ratio(rgb(token("ink")), fill)).toBeGreaterThanOrEqual(7);
    });
    it(`${name}: supporting text (--ink-2, --caption, --eyebrow) is at least 4.5:1`, () => {
      for (const text of ["ink-2", "caption", "eyebrow"]) {
        expect(ratio(rgb(token(text)), fill), text).toBeGreaterThanOrEqual(4.5);
      }
    });
    it(`${name}: --brand text (tabs, glass buttons) is at least 4.5:1`, () => {
      expect(ratio(brand, fill)).toBeGreaterThanOrEqual(4.5);
    });
  }

  it("field: text, placeholder and error text pass on the field fill", () => {
    const fill = over(surface, percent("glass-field-alpha"), glow);
    expect(ratio(rgb(token("ink")), fill)).toBeGreaterThanOrEqual(7);
    expect(ratio(rgb(token("caption")), fill)).toBeGreaterThanOrEqual(4.5);
    expect(ratio(rgb(token("scam-fg")), fill)).toBeGreaterThanOrEqual(4.5);
  });

  it("primary glass button: --on-brand text is at least 4.5:1 on brand-tinted glass over white", () => {
    const fill = over(brand, percent("glass-solid-alpha"), surface);
    expect(ratio(rgb(token("on-brand")), fill)).toBeGreaterThanOrEqual(4.5);
  });

  it("the focus ring (--brand) is at least 3:1 against the tier 1 glass", () => {
    expect(ratio(brand, over(surface, tiers["tier 1"], glow))).toBeGreaterThanOrEqual(3);
  });
});

describe("glass.css rules", () => {
  const css = glass.replace(/\/\*[\s\S]*?\*\//g, "");

  it("invents no colour values: only brand tokens, color-mix() and the #000 mask stop", () => {
    const hex = css.match(/#[0-9a-fA-F]{3,8}\b/g)?.filter((value) => value.toLowerCase() !== "#000") ?? [];
    expect(hex).toEqual([]);
    expect(css).not.toMatch(/\brgba?\(/);
  });

  it("falls back to solid tokens without backdrop-filter, color-mix, transparency or colours", () => {
    expect(css).toContain("@supports not ((backdrop-filter: blur(1px))");
    expect(css).toContain("@supports not (background: color-mix(");
    expect(css).toContain("prefers-reduced-transparency: reduce");
    expect(css).toContain("prefers-contrast: more");
    expect(css).toContain("forced-colors: active");
  });

  it("every fallback also covers the sticky mobile submit bar", () => {
    // .scan-submit (styles.css) uses the tier 3 fill and blur, so each fallback must override it.
    const blocks = [
      "@supports not ((backdrop-filter: blur(1px))",
      "@media (prefers-reduced-transparency: reduce), (prefers-contrast: more)",
      "@media (forced-colors: active)",
    ];
    for (const start of blocks) {
      const from = css.indexOf(start);
      expect(from, start).toBeGreaterThan(-1);
      const next = css.indexOf("\n}\n", from);
      expect(css.slice(from, next), start).toContain(".glass-stage .scan-submit");
    }
  });

  it("orders the tiers from most transparent to most opaque", () => {
    expect(tiers["tier 1"]).toBeLessThan(tiers["tier 2"]);
    expect(tiers["tier 2"]).toBeLessThan(tiers["tier 3"]);
  });
});
