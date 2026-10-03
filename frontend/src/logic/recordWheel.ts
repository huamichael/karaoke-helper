/**
 * The song screen's record wheel, as numbers.
 *
 * The wheel's position u is unbounded: u = 0 is the first song, u = 1 the next,
 * and it loops, so song = u mod n. The record turns 40° per song. The selected
 * song sits at the needle (180°, the record's left edge), one above, one below.
 *
 * Owner: A. Spec: docs/design/ui.md §3.3 ("Spinning the record") and §5.1.
 */

export const STEP_DEG = 40;
/** Wheel and trackpad pixels per song. */
export const WHEEL_PX_PER_SONG = 420;
/** Drag pixels per song. */
export const DRAG_PX_PER_SONG = 150;

export const mod = (a: number, n: number) => ((a % n) + n) % n;

export function selectedIndex(u: number, n: number): number {
  return mod(Math.round(u), n);
}

/** How much of each song's photo and cover shows at position u. Sums to 1. */
export function crossfadeWeights(u: number, n: number): number[] {
  const w = new Array<number>(n).fill(0);
  for (let j = Math.floor(u) - 1; j <= Math.ceil(u) + 1; j++) {
    const k = mod(j, n);
    w[k] += Math.max(0, 1 - Math.abs(j - u));
  }
  return w;
}

/** 0 on a song, 1 halfway between two: drives the static and the grain. */
export function betweenAmount(u: number): number {
  return Math.min(1, Math.abs(u - Math.round(u)) * 2);
}

export type Slot = { key: number; song: number; angleDeg: number; x: number; y: number; scale: number; opacity: number; selected: boolean };

/** The song names riding the groove band: at most three in view, plus one fading in or out. */
export function labelSlots(u: number, n: number, g: { cx: number; cy: number; rn: number }): Slot[] {
  const base = Math.round(u);
  const out: Slot[] = [];
  for (let j = base - 2; j <= base + 2; j++) {
    const d = Math.abs(j - u);
    if (d > 1.55) continue;
    const angleDeg = 180 - (j - u) * STEP_DEG;
    const t = (angleDeg * Math.PI) / 180;
    out.push({
      key: j,
      song: mod(j, n),
      angleDeg,
      x: g.cx + g.rn * Math.cos(t),
      y: g.cy + g.rn * Math.sin(t), // screen y points down, so the next song (j > u) sits below the needle
      scale: 1 - Math.min(d, 1) * 0.22,
      opacity: d <= 1 ? 1 - d * 0.4 : Math.max(0, (0.6 * (1.5 - d)) / 0.5),
      selected: j === base,
    });
  }
  return out;
}

/** Sizes in px. dialLeft/dialTop: where the wheel's box sits in the window. */
export function wheelGeometry(W: number, H: number, dialLeft: number, dialTop: number) {
  const R = Math.min(H * 0.56, W * 0.36);
  const rl = R * 0.44; // label radius
  const rn = (R - 44 + rl + 8) / 2; // the names ride halfway between the needle and the label
  const cx = W - R * 0.46 - dialLeft;
  const cy = H / 2 - dialTop;
  return { R, rl, rn, nameMax: R - rl - 52, cx, cy, discLeft: dialLeft + cx - R };
}

/** Where a wheel or trackpad gesture settles: back if barely moved, else at least one song on. */
export function wheelSettle(start: number, raw: number): number {
  const moved = raw - start;
  if (Math.abs(moved) <= 0.12) return start;
  return start + Math.sign(moved) * Math.max(1, Math.round(Math.abs(moved)));
}

/** Where a drag settles, carrying its speed (songs per second) a little further. */
export function dragSettle(u: number, v: number): number {
  return Math.round(u + v * 0.18);
}

/** One frame of the settling spring. */
export function stepSpring(s: { u: number; v: number }, target: number, dt: number): { u: number; v: number; done: boolean } {
  const v = s.v + (130 * (target - s.u) - 22 * s.v) * dt;
  const u = s.u + v * dt;
  if (Math.abs(target - u) < 0.0008 && Math.abs(v) < 0.003) return { u: target, v: 0, done: true };
  return { u, v, done: false };
}
