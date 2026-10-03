/**
 * The app's two springs, sampled into CSS linear() easings so CSS and
 * JavaScript share them.
 *
 * LINE_SPRING (slight overshoot, ~500 ms) moves between lines.
 * SOFT_SPRING (almost none, ~300 ms) resizes the dock and the options pill.
 *
 * Owner: A. Spec: docs/design/ui.md §3.3.
 */

export type SampledSpring = { points: number[]; durationMs: number };

/** Simulate a damped spring from 0 to 1 and keep `samples + 1` evenly spaced points. */
export function sampleSpring(stiffness: number, damping: number, samples = 48): SampledSpring {
  const dt = 1 / 240;
  let x = 0, v = 0, t = 0;
  const trace = [0];
  while (t < 1.5) {
    v += (-stiffness * (x - 1) - damping * v) * dt;
    x += v * dt;
    t += dt;
    trace.push(x);
    if (t > 0.2 && Math.abs(x - 1) < 0.0015 && Math.abs(v) < 0.02) break;
  }
  const points: number[] = [];
  for (let s = 0; s <= samples; s++) points.push(+trace[Math.round((s / samples) * (trace.length - 1))].toFixed(4));
  points[samples] = 1;
  return { points, durationMs: Math.round(t * 1000) };
}

export const linearEasing = (points: number[]) => `linear(${points.join(", ")})`;

export const LINE_SPRING = sampleSpring(210, 23);
export const SOFT_SPRING = sampleSpring(320, 34);
