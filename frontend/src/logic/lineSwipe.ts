/**
 * Turns wheel, trackpad and touch input into "up one line" or "down one line".
 *
 * One gesture moves one line. A trackpad swipe and its momentum tail are one
 * gesture; wheel-gestures tells a fresh swipe apart from the previous one's
 * momentum. One deliberate mouse-wheel notch is one gesture.
 *
 * Owner: A. Spec: docs/design/ui.md §5.3.2.
 */
import { WheelGestures, type WheelEventData } from "wheel-gestures";

/** +1 is the next line, -1 the previous one. */
export type Step = 1 | -1;

/** Pixels a gesture must travel before it counts. */
export const WHEEL_THRESHOLD = 28;
export const TOUCH_DISTANCE = 48;
/** px/ms: a quick flick moves a line even when it is short. */
export const TOUCH_FLICK = 0.5;

export function createWheelStepper(onStep: (dir: Step) => void, threshold = WHEEL_THRESHOLD) {
  const wg = WheelGestures({ preventWheelAction: "y", reverseSign: false });
  let acc = 0;
  let used = false;
  wg.on("wheel", (s) => {
    if (s.isStart) {
      acc = 0;
      used = false;
    }
    if (s.isEnding || used) return;
    const [dx, dy] = s.axisDelta;
    if (Math.abs(dx) > Math.abs(dy)) return;
    acc += dy;
    if (Math.abs(acc) >= threshold) {
      used = true;
      onStep(acc > 0 ? 1 : -1);
    }
  });
  return {
    observe: (target: EventTarget) => wg.observe(target),
    feed: (e: WheelEventData) => wg.feedWheel(e),
    disconnect: () => wg.disconnect(),
  };
}

/** On release: dy is how far the finger moved (negative = up), v its speed in px/ms. */
export function touchStep(dy: number, v: number): Step | 0 {
  if (Math.abs(dy) > TOUCH_DISTANCE) return dy < 0 ? 1 : -1;
  if (Math.abs(v) > TOUCH_FLICK) return v < 0 ? 1 : -1;
  return 0;
}

/** How far the list follows the finger: fully, stretched past the ends, barely while locked. */
export function touchFollow(dy: number, o: { locked: boolean; atEnd: boolean }): number {
  if (o.locked) return dy * 0.12;
  if (o.atEnd) return dy * 0.35;
  return dy;
}
