/**
 * The song screen's turntable, as numbers: the platter's speed, the cover's
 * play/pause glyph, and where the tonearm sits.
 *
 * Arm on the record = playing; arm on its rest = stopped. The platter spins up
 * when it plays and slows to a stop after the arm is back on its rest.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("The tonearm", "It behaves like a real turntable").
 */

/** Degrees a second: slower than a real 33⅓, for calm. */
export const PLATTER_SPEED = 30;

/** One frame of the platter: it eases up over ~0.5 s and down over ~0.7 s, then stops dead. */
export function platterStep(speed: number, target: number, dt: number): number {
  const next = speed + (target - speed) * Math.min(1, dt / (target > speed ? 0.5 : 0.7));
  return target === 0 && next < 0.4 ? 0 : next;
}

type Pt = [number, number];
/** The two pause bars, and the two halves of the play triangle they fold into (viewBox 0 0 36 36). */
const PAUSE: Pt[][] = [[[12.6, 25.4], [15.4, 25.4], [15.4, 10.6], [12.6, 10.6]], [[20.6, 25.4], [23.4, 25.4], [23.4, 10.6], [20.6, 10.6]]];
const PLAY: Pt[][] = [[[12.6, 25], [18.25, 21.5], [18.25, 14.5], [12.6, 11]], [[18.25, 21.5], [23.9, 18], [23.9, 18], [18.25, 14.5]]];

/** The cover glyph at t: 0 = pause bars, 1 = play triangle, in between = folding, as on YouTube. */
export function glyphPaths(t: number): [string, string] {
  const path = (k: number) =>
    "M" + PAUSE[k].map(([x, y], i) => {
      const [X, Y] = PLAY[k][i];
      return `${(x + (X - x) * t).toFixed(2)} ${(y + (Y - y) * t).toFixed(2)}`;
    }).join(" ") + "z";
  return [path(0), path(1)];
}

export type ArmLayout = {
  /** The arm's pivot, in the dial's own pixels. */
  pivot: { x: number; y: number };
  /** Where the stylus sets down: the record's lead-in, just above the selected song. */
  leadIn: { x: number; y: number };
  /** Where the arm rest stands. */
  rest: { x: number; y: number };
  /** Pivot to stylus, px. */
  length: number;
  /** Screen angles of the arm, radians, measured from the pivot. */
  playAngle: number;
  restAngle: number;
  /** How far the cue lever tilts the arm, radians: about 24px at the stylus. */
  lift: number;
};

export function armLayout(g: { cx: number; cy: number; R: number }, w: number, _h: number): ArmLayout {
  const pivot = { x: w - 72, y: 82 };
  const a = (190 * Math.PI) / 180;
  const leadIn = { x: g.cx + g.R * 0.86 * Math.cos(a), y: g.cy + g.R * 0.86 * Math.sin(a) };
  const length = Math.hypot(leadIn.x - pivot.x, leadIn.y - pivot.y);
  const restAngle = (184 * Math.PI) / 180;
  return {
    pivot,
    leadIn,
    rest: { x: pivot.x + Math.cos(restAngle) * length * 0.5, y: pivot.y + Math.sin(restAngle) * length * 0.5 },
    length,
    playAngle: Math.atan2(leadIn.y - pivot.y, leadIn.x - pivot.x),
    restAngle,
    lift: 24 / length,
  };
}
