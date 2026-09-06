/* Contrast gate over tokens.css.
 *
 * A palette is a claim about legibility. This measures it. Every value in
 * tokens.css that carries text must clear 4.5:1 against the ground it sits on,
 * and every token that draws a control boundary must clear 3:1 — in BOTH
 * registers, because a light theme built by inverting a dark one fails exactly
 * the places nobody looks.
 *
 * Out-of-gamut OKLCH values are clamped in linear light before luminance is
 * taken, which is what the browser effectively renders. Measured ratios are
 * written to docs/results/A2-contrast.json so the design doc can cite them
 * instead of asserting them.
 */

import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, "../../..");
const TOKENS = resolve(HERE, "../styles/tokens.css");
const OUT = resolve(REPO, "docs/results/A2-contrast.json");

// ── colour ──────────────────────────────────────────────────────────────────

const clamp01 = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);

/** OKLCH → linear sRGB (clamped to gamut). */
function oklchToLinearSrgb(L, C, H) {
  const h = (H * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);
  const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = L - 0.0894841775 * a - 1.291485548 * b;
  const l = l_ ** 3;
  const m = m_ ** 3;
  const s = s_ ** 3;
  return [
    clamp01(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
    clamp01(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
    clamp01(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s),
  ];
}

const luminance = ([r, g, b]) => 0.2126 * r + 0.7152 * g + 0.0722 * b;

function contrast(fg, bg) {
  const a = luminance(fg);
  const b = luminance(bg);
  const [hi, lo] = a > b ? [a, b] : [b, a];
  return (hi + 0.05) / (lo + 0.05);
}

const toHex = (lin) =>
  "#" +
  lin
    .map((v) => {
      const s = v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055;
      return Math.round(clamp01(s) * 255)
        .toString(16)
        .padStart(2, "0");
    })
    .join("");

// ── parse ───────────────────────────────────────────────────────────────────

/* Registers are delimited by explicit `@register <name>` marker comments so the
 * parser stays trivial and cannot be confused by nested at-rules. */
function parseRegisters(css) {
  const registers = {};
  let current = null;
  for (const raw of css.split("\n")) {
    const marker = raw.match(/@register\s+([a-z]+)/);
    if (marker) {
      current = marker[1];
      registers[current] ??= {};
      continue;
    }
    if (!current) continue;
    const decl = raw.match(
      /^\s*(--[a-z0-9-]+)\s*:\s*oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*(?:\/\s*[\d.]+\s*)?\)/i,
    );
    if (decl) {
      const [, name, L, C, H] = decl;
      registers[current][name] = {
        oklch: [Number(L), Number(C), Number(H)],
        linear: oklchToLinearSrgb(Number(L), Number(C), Number(H)),
      };
    }
  }
  return registers;
}

// ── the contract ────────────────────────────────────────────────────────────

const TEXT_MIN = 4.5;
const UI_MIN = 3.0;

/** [foreground, background, floor, why]. Applied to every register. */
const PAIRS = [
  ["--text", "--bg", TEXT_MIN, "body text on the ground"],
  ["--text", "--surface", TEXT_MIN, "body text on a card"],
  ["--text", "--surface-raised", TEXT_MIN, "body text on a raised card"],
  ["--text-muted", "--bg", TEXT_MIN, "secondary text"],
  ["--text-muted", "--surface", TEXT_MIN, "secondary text on a card"],
  ["--text-faint", "--bg", TEXT_MIN, "metadata — smallest type in the app, so still body text"],
  ["--text-faint", "--surface", TEXT_MIN, "metadata on a card"],
  ["--border-strong", "--bg", UI_MIN, "control boundary: inputs, buttons, table heads"],
  ["--border-strong", "--surface", UI_MIN, "control boundary on a card"],
  ["--seat-cfo-text", "--bg", TEXT_MIN, "CFO attribution"],
  ["--seat-cmo-text", "--bg", TEXT_MIN, "CMO attribution"],
  ["--seat-coo-text", "--bg", TEXT_MIN, "COO attribution"],
  ["--seat-ethics-text", "--bg", TEXT_MIN, "Ethics Officer attribution"],
  ["--seat-devil-text", "--bg", TEXT_MIN, "Devil's Advocate attribution"],
  ["--seat-cfo-text", "--surface", TEXT_MIN, "CFO attribution on a card"],
  ["--seat-cmo-text", "--surface", TEXT_MIN, "CMO attribution on a card"],
  ["--seat-coo-text", "--surface", TEXT_MIN, "COO attribution on a card"],
  ["--seat-ethics-text", "--surface", TEXT_MIN, "Ethics attribution on a card"],
  ["--seat-devil-text", "--surface", TEXT_MIN, "Devil's Advocate attribution on a card"],
  ["--text-on-seat", "--seat-cfo", TEXT_MIN, "text knocked out of a CFO fill"],
  ["--text-on-seat", "--seat-cmo", TEXT_MIN, "text knocked out of a CMO fill"],
  ["--text-on-seat", "--seat-coo", TEXT_MIN, "text knocked out of a COO fill"],
  ["--text-on-seat", "--seat-ethics", TEXT_MIN, "text knocked out of an Ethics fill"],
  ["--text-on-seat", "--seat-devil", TEXT_MIN, "text knocked out of a Devil fill"],
];

/* Measured and published, but NOT gated — and the reason is stated rather than
 * left for a reviewer to discover. --border is a hairline rule between rows of
 * a document. It is not a control boundary and never encloses one; --border-strong
 * does that job and is gated at 3:1 above. */
const UNGATED = [
  ["--border", "--bg", "hairline rule between record rows — decorative, not a control boundary"],
  ["--rule-margin", "--bg", "the margin rule the Record column hangs on — structure, not a control boundary"],
];

// ── run ─────────────────────────────────────────────────────────────────────

const registers = parseRegisters(readFileSync(TOKENS, "utf8"));
const names = Object.keys(registers);
if (names.length < 2) {
  console.error(`contrast gate FAILED — expected 2 registers, found ${names.length}: ${names}`);
  process.exit(1);
}

const report = { generated_by: "apps/web/scripts/check-contrast.mjs", floors: { text: TEXT_MIN, ui: UI_MIN }, registers: {} };
const failures = [];

for (const register of names) {
  const tokens = registers[register];
  const rows = [];
  for (const [fg, bg, floor, why] of PAIRS) {
    if (!tokens[fg] || !tokens[bg]) {
      failures.push(`${register}: missing token ${!tokens[fg] ? fg : bg}`);
      continue;
    }
    const ratio = contrast(tokens[fg].linear, tokens[bg].linear);
    const pass = ratio >= floor;
    rows.push({ fg, bg, ratio: Number(ratio.toFixed(2)), floor, pass, why });
    if (!pass) {
      failures.push(`${register}: ${fg} on ${bg} measured ${ratio.toFixed(2)}:1, needs ${floor}:1 — ${why}`);
    }
  }
  for (const [fg, bg, why] of UNGATED) {
    if (!tokens[fg] || !tokens[bg]) continue;
    rows.push({
      fg, bg, ratio: Number(contrast(tokens[fg].linear, tokens[bg].linear).toFixed(2)),
      floor: null, pass: null, why,
    });
  }
  report.registers[register] = {
    swatches: Object.fromEntries(Object.entries(tokens).map(([k, v]) => [k, toHex(v.linear)])),
    pairs: rows,
  };
}

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify(report, null, 2) + "\n");

if (failures.length) {
  console.error(`contrast gate FAILED — ${failures.length} pair(s) below floor:`);
  for (const f of failures) console.error(`  ${f}`);
  process.exit(1);
}

const total = Object.values(report.registers).reduce((n, r) => n + r.pairs.length, 0);
console.log(`contrast gate clean — ${total} pairs measured across ${names.length} registers, written to docs/results/A2-contrast.json`);
