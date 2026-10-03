/**
 * The collage where the record meets the photo: the record is a torn-paper
 * cut-out pasted onto the photograph, and three scraps cut from the song's own
 * photo overlap its rim, each a different shape.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("Collage where the record meets the photo").
 */

export type Scrap = {
  /** Which of the theme's three focus points it shows. */
  i: number;
  /** Angle on the record (180° = the needle) and distance from the centre as a share of R. */
  a: number;
  r: number;
  /** Size at R = 504px, and tilt. */
  w: number;
  h: number;
  rot: number;
  /** How much larger the photo detail is than in the background. */
  zoom: number;
  /** A strip of tape: left %, top px, rotation. */
  tape?: [number, number, number];
  /** The cut outline, in % of the scrap's box. */
  poly: [number, number][];
};

/** A round cut that echoes the record, slightly irregular. */
export function roundCut(n = 30): [number, number][] {
  return Array.from({ length: n }, (_, k) => {
    const t = (k / n) * Math.PI * 2, f = 1 + 0.035 * Math.sin(3 * t) + 0.02 * Math.sin(7 * t + 1);
    return [50 + 49 * Math.cos(t) * f, 50 + 49 * Math.sin(t) * f];
  });
}

export const SCRAPS: Scrap[] = [
  { i: 0, a: 212, r: 1.0, w: 196, h: 124, rot: -5, zoom: 1.5, tape: [60, -10, 8],
    poly: [[2, 10], [18, 2], [41, 7], [63, 0], [88, 5], [99, 22], [95, 48], [100, 77], [90, 97], [64, 93], [38, 100], [13, 94], [0, 71], [5, 42]] },
  { i: 1, a: 168, r: 1.04, w: 50, h: 138, rot: 8, zoom: 1.7,
    poly: [[8, 0], [52, 3], [96, 0], [100, 14], [92, 30], [100, 47], [94, 63], [100, 80], [96, 100], [50, 97], [4, 100], [0, 82], [7, 64], [0, 45], [6, 27], [0, 10]] },
  { i: 2, a: 154, r: 0.99, w: 118, h: 112, rot: -4, zoom: 1.8, poly: roundCut() },
];

/** The scrap's box in the dial's pixels. */
export function scrapBox(s: Scrap, g: { cx: number; cy: number; R: number }) {
  const k = g.R / 504, t = (s.a * Math.PI) / 180, w = s.w * k, h = s.h * k;
  return { x: g.cx + g.R * s.r * Math.cos(t) - w / 2, y: g.cy + g.R * s.r * Math.sin(t) - h / 2, w, h };
}

/** The photo's size inside a scrap: the background's cover crop (106% of the window), enlarged by zoom. */
export function scrapPhotoSize(photo: [number, number], W: number, H: number, zoom: number): [number, number] {
  const f = Math.max((W * 1.06) / photo[0], (H * 1.06) / photo[1]) * zoom;
  return [photo[0] * f, photo[1] * f];
}

/** A torn-edged circle as a CSS mask: an SVG circle displaced by turbulence. */
export function tornMask(seed: number, r: number, scale: number): string {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000'><filter id='t' x='-8%' y='-8%' width='116%' height='116%'><feTurbulence type='fractalNoise' baseFrequency='.016' numOctaves='5' seed='${seed}'/><feDisplacementMap in='SourceGraphic' scale='${scale}' xChannelSelector='R' yChannelSelector='G'/></filter><circle cx='500' cy='500' r='${r}' fill='#fff' filter='url(#t)'/></svg>`;
  return `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}")`;
}
