import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

/**
 * The palette lives in index.css, so it can drift without any component
 * changing. These tests read the stylesheet itself and check that every
 * foreground/background pair the UI actually puts together stays legible in
 * both themes.
 */

const css = readFileSync(join(process.cwd(), "src/index.css"), "utf8");

function block(header: string): Record<string, string> {
  const start = css.indexOf(header);
  if (start < 0) throw new Error(`no ${header} block in index.css`);
  const body = css.slice(start + header.length, css.indexOf("\n}", start));
  const tokens: Record<string, string> = {};
  for (const [, name, value] of body.matchAll(/(--color-[\w-]+):\s*([^;]+);/g)) {
    tokens[name] = value.trim();
  }
  return tokens;
}

const base = block("@theme {");
const darkOverrides = block('html[data-theme="dark"] {');
const themes = { light: base, dark: { ...base, ...darkOverrides } };

type Rgb = [number, number, number];

/** Resolve a token to rgb, following var() and compositing color-mix over `backdrop`. */
function resolve(tokens: Record<string, string>, value: string, backdrop: Rgb): Rgb {
  const raw = value.trim();

  const hex = /^#([0-9a-f]{6})$/i.exec(raw);
  if (hex) {
    const n = parseInt(hex[1], 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => c / 255) as Rgb;
  }

  const variable = /^var\((--color-[\w-]+)\)$/.exec(raw);
  if (variable) return resolve(tokens, tokens[variable[1]], backdrop);

  // color-mix(in srgb, <colour> <pct>%, transparent) is an alpha over the backdrop.
  const mix = /^color-mix\(in srgb,\s*(.+?)\s+([\d.]+)%,\s*transparent\)$/.exec(raw);
  if (mix) {
    const front = resolve(tokens, mix[1], backdrop);
    const alpha = Number(mix[2]) / 100;
    return front.map((c, i) => c * alpha + backdrop[i] * (1 - alpha)) as Rgb;
  }

  throw new Error(`cannot resolve colour: ${raw}`);
}

function luminance([r, g, b]: Rgb): number {
  const channel = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function contrast(foreground: Rgb, background: Rgb): number {
  const a = luminance(foreground);
  const b = luminance(background);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

/** [foreground token, background token, minimum ratio, what it is] */
const pairs: [string, string, number, string][] = [
  ["--color-ink", "--color-surface", 4.5, "body text on the page"],
  ["--color-ink", "--color-raised", 4.5, "body text on a card"],
  ["--color-ink-muted", "--color-raised", 4.5, "secondary text on a card"],
  ["--color-ink-subtle", "--color-raised", 3, "hint text on a card"],
  ["--color-brand", "--color-raised", 4.5, "a brand link on a card"],
  ["--color-success", "--color-success-soft", 4.5, "a success badge"],
  ["--color-warning", "--color-warning-soft", 4.5, "a warning badge"],
  ["--color-danger", "--color-danger-soft", 4.5, "a danger badge"],
  ["--color-info", "--color-info-soft", 4.5, "an info badge"],
  ["--color-danger", "--color-raised", 4.5, "destructive button text"],
];

describe.each(Object.entries(themes))("%s theme", (_name, tokens) => {
  const page = resolve(tokens, tokens["--color-surface"], [1, 1, 1]);

  it.each(pairs)("%s on %s stays legible (%s:1, %s)", (fg, bg, minimum) => {
    const background = resolve(tokens, tokens[bg], page);
    const foreground = resolve(tokens, tokens[fg], background);
    expect(contrast(foreground, background)).toBeGreaterThanOrEqual(minimum);
  });
});

describe("both themes", () => {
  it("keeps white readable on the filled brand button", () => {
    // The primary action keeps brand copper in both themes, so it is checked once.
    const copper = resolve(base, base["--color-copper"], [1, 1, 1]);
    expect(contrast([1, 1, 1], copper)).toBeGreaterThanOrEqual(4.5);
  });

  it("keeps white readable on the filled danger badge", () => {
    // Overdue reminders are the one filled status, held at one value everywhere.
    const solid = resolve(base, base["--color-danger-solid"], [1, 1, 1]);
    expect(contrast([1, 1, 1], solid)).toBeGreaterThanOrEqual(4.5);
    expect(darkOverrides["--color-danger-solid"]).toBeUndefined();
  });

  it("gives every semantic token a value in both themes", () => {
    const semantic = Object.keys(base).filter((name) =>
      /^--color-(surface|raised|sunken|line|ink|brand|success|warning|danger|info)/.test(name),
    );
    for (const name of semantic) {
      expect(themes.light[name], `${name} in light`).toBeDefined();
      expect(themes.dark[name], `${name} in dark`).toBeDefined();
    }
  });
});
