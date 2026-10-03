import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createWheelStepper, touchFollow, touchStep, type Step } from "./lineSwipe";

/** Wheel events as a browser sends them: deltaY in pixels, ~16 ms apart. */
type Ev = { deltaX?: number; deltaY: number; dt?: number };

/** A trackpad swipe: the finger ramps up, lifts, and a long momentum tail decays. */
function trackpadSwipe(sign = 1, peak = 30): Ev[] {
  const finger = [1, 3, 6, 12, 20, peak, peak, 26].map((d) => ({ deltaY: sign * d }));
  const tail: Ev[] = [];
  for (let d = 24; d >= 1; d *= 0.9) tail.push({ deltaY: sign * Math.round(d * 10) / 10 });
  return [...finger, ...tail];
}

describe("createWheelStepper", () => {
  let steps: Step[];
  let t: number;
  let stepper: ReturnType<typeof createWheelStepper>;

  const feed = (events: Ev[]) => {
    for (const e of events) {
      const dt = e.dt ?? 16;
      vi.advanceTimersByTime(dt);
      t += dt;
      stepper.feed({ deltaX: e.deltaX ?? 0, deltaY: e.deltaY, deltaMode: 0, timeStamp: t });
    }
  };
  const pause = (ms: number) => {
    vi.advanceTimersByTime(ms);
    t += ms;
  };

  beforeEach(() => {
    vi.useFakeTimers();
    steps = [];
    t = 1000;
    stepper = createWheelStepper((d) => steps.push(d));
  });
  afterEach(() => {
    stepper.disconnect();
    vi.useRealTimers();
  });

  it("turns one trackpad swipe with a long momentum tail into exactly one step", () => {
    feed(trackpadSwipe());
    pause(1200);
    expect(steps).toEqual([1]);
  });

  it("steps backwards for an upward swipe", () => {
    feed(trackpadSwipe(-1));
    pause(1200);
    expect(steps).toEqual([-1]);
  });

  it("gives two steps for two swipes with a pause between", () => {
    feed(trackpadSwipe());
    pause(1200);
    feed(trackpadSwipe());
    pause(1200);
    expect(steps).toEqual([1, 1]);
  });

  it("counts a fresh swipe that interrupts the previous momentum", () => {
    const first = trackpadSwipe();
    feed(first.slice(0, first.length - 8)); // stop while the tail is still coming in
    feed(trackpadSwipe(1, 40).slice(2));
    pause(1200);
    expect(steps).toEqual([1, 1]);
  });

  it("gives one step per deliberate mouse-wheel notch", () => {
    feed([{ deltaY: 100, dt: 500 }, { deltaY: 100, dt: 500 }, { deltaY: -100, dt: 500 }]);
    pause(1200);
    expect(steps).toEqual([1, 1, -1]);
  });

  it("ignores a small nudge", () => {
    feed([{ deltaY: 2 }, { deltaY: 4 }, { deltaY: 3 }]);
    pause(1200);
    expect(steps).toEqual([]);
  });

  it("ignores sideways swipes", () => {
    feed([5, 15, 30, 40, 30, 20].map((d) => ({ deltaX: d, deltaY: d / 6 })));
    pause(1200);
    expect(steps).toEqual([]);
  });
});

describe("touchStep", () => {
  it("moves to the next line after dragging up past 48px", () => {
    expect(touchStep(-60, 0)).toBe(1);
  });
  it("moves to the previous line after dragging down past 48px", () => {
    expect(touchStep(60, 0)).toBe(-1);
  });
  it("springs back after a short, slow drag", () => {
    expect(touchStep(30, 0.1)).toBe(0);
  });
  it("moves on a quick flick even when short", () => {
    expect(touchStep(-12, -0.8)).toBe(1);
    expect(touchStep(10, 0.7)).toBe(-1);
  });
});

describe("touchFollow", () => {
  it("follows the finger when the line can change", () => {
    expect(touchFollow(-40, { locked: false, atEnd: false })).toBe(-40);
  });
  it("stretches a little past the first or last line", () => {
    expect(touchFollow(-40, { locked: false, atEnd: true })).toBeCloseTo(-14);
  });
  it("barely moves while locked", () => {
    expect(touchFollow(-50, { locked: true, atEnd: false })).toBeCloseTo(-6);
  });
});
