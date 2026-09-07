/* Where the seats sit, and how an argument arcs between them.
 *
 * Angles are FIXED. A replay must seat the same people in the same chairs as
 * the recording, so nothing here is derived from data that could change between
 * runs — not the number of turns, not who spoke most, not anything. The seat
 * order matches SEATING in services/api/crew/mandate.py and the CSS tokens.
 */

export const SEATS = ["cfo", "cmo", "coo", "ethics", "devil"] as const;
export type Seat = (typeof SEATS)[number];

/* Five chairs, evenly spaced, starting at the top and going clockwise so the
 * reading order on screen matches the seating order in the transcript. */
export const SEAT_ANGLES: Record<Seat, number> = SEATS.reduce(
  (acc, seat, i) => ({ ...acc, [seat]: (i / SEATS.length) * Math.PI * 2 - Math.PI / 2 }),
  {} as Record<Seat, number>,
);

export function seatXZ(seat: Seat, radius: number): [number, number] {
  const a = SEAT_ANGLES[seat];
  return [Math.cos(a) * radius, Math.sin(a) * radius];
}

/* An arc that bows toward the centre, so two seats opposite each other do not
 * draw a line straight through the table and every edge stays readable. */
export function arcPoints(
  from: Seat,
  to: Seat,
  radius: number,
  segments = 24,
): [number, number][] {
  const [x1, z1] = seatXZ(from, radius);
  const [x2, z2] = seatXZ(to, radius);
  const cx = ((x1 + x2) / 2) * 0.25;
  const cz = ((z1 + z2) / 2) * 0.25;
  return Array.from({ length: segments + 1 }, (_, i) => {
    const t = i / segments;
    const u = 1 - t;
    return [
      u * u * x1 + 2 * u * t * cx + t * t * x2,
      u * u * z1 + 2 * u * t * cz + t * t * z2,
    ] as [number, number];
  });
}

/* How lit a seat is: 1.0 for whoever is speaking now, falling away over the
 * turns before it. Recency, not volume — a seat that talked a lot earlier does
 * not stay bright, because that would read as importance. */
export function glow(seatTurnOrdinal: number | null, activeOrdinal: number): number {
  if (seatTurnOrdinal === null) return 0;
  const distance = activeOrdinal - seatTurnOrdinal;
  if (distance < 0) return 0;
  return Math.max(0, 1 - distance / 6);
}

export function isWebGLAvailable(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext("webgl2") || canvas.getContext("webgl")),
    );
  } catch {
    return false;
  }
}

/* Any CSS colour to hex, because three.js parses almost none of them.
 *
 * The seat colours live in tokens.css as oklch(), which is the right place for
 * them: one definition, shared by the margin rail and the table, so the two
 * cannot drift. But THREE.Color takes hex or rgb, and getComputedStyle does not
 * hand back what was written.
 *
 * Measured in this browser: reading `--seat-cfo` returns
 * `lab(38.1738% 47.3605 28.6629)`, not the oklch() in the stylesheet, because
 * the engine normalises to CIE Lab. Passing it through a canvas 2D context —
 * the usual trick for normalising a CSS colour — returns lab() as well: this
 * engine preserves the colour space rather than flattening to rgb.
 *
 * So both spaces are parsed here. It is more code than a hardcoded palette
 * would be, and it keeps tokens.css as the only place a seat colour is defined.
 */
const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);

function linearToHex(lin: number[]): string {
  return (
    "#" +
    lin
      .map((v) => {
        const srgb = v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055;
        return Math.round(clamp01(srgb) * 255)
          .toString(16)
          .padStart(2, "0");
      })
      .join("")
  );
}

/** CIE Lab (D50, as CSS Color 4 defines it) to linear sRGB. */
function labToLinearSrgb(L: number, a: number, b: number): number[] {
  const K = 24389 / 27;
  const E = 216 / 24389;
  const fy = (L + 16) / 116;
  const fx = fy + a / 500;
  const fz = fy - b / 200;

  const xr = fx ** 3 > E ? fx ** 3 : (116 * fx - 16) / K;
  const yr = L > K * E ? ((L + 16) / 116) ** 3 : L / K;
  const zr = fz ** 3 > E ? fz ** 3 : (116 * fz - 16) / K;

  // D50 white point, then Bradford-adapted XYZ(D50) to linear sRGB.
  const [X, Y, Z] = [xr * 0.9642956764295677, yr, zr * 0.8251046025104602];
  return [
    3.1341359569958707 * X - 1.6173863321612522 * Y - 0.4906619460083532 * Z,
    -0.978795502912089 * X + 1.916254567259524 * Y + 0.03344273116131949 * Z,
    0.07195537988411677 * X - 0.2289768264158322 * Y + 1.405386058324125 * Z,
  ].map(clamp01);
}

/** OKLCH to linear sRGB — the same maths the contrast gate uses. */
function oklchToLinearSrgb(L: number, C: number, H: number): number[] {
  const h = (H * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ].map(clamp01);
}

export function cssColourToHex(css: string): string | null {
  if (!css) return null;
  const trimmed = css.trim();
  if (/^#[0-9a-f]{3,8}$/i.test(trimmed)) return trimmed;

  const lab = trimmed.match(/^lab\(\s*([\d.+-]+)%?\s+([\d.+-]+)\s+([\d.+-]+)/i);
  if (lab) return linearToHex(labToLinearSrgb(Number(lab[1]), Number(lab[2]), Number(lab[3])));

  const oklch = trimmed.match(/^oklch\(\s*([\d.]+)%?\s+([\d.]+)\s+([\d.]+)/i);
  if (oklch) {
    const L = trimmed.includes("%") ? Number(oklch[1]) / 100 : Number(oklch[1]);
    return linearToHex(oklchToLinearSrgb(L, Number(oklch[2]), Number(oklch[3])));
  }

  const rgb = trimmed.match(/^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)/i);
  if (rgb) {
    return (
      "#" +
      rgb
        .slice(1, 4)
        .map((v) => Math.round(Number(v)).toString(16).padStart(2, "0"))
        .join("")
    );
  }
  return null;
}
