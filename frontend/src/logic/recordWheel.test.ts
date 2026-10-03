import { describe, expect, it } from "vitest";
import {
  betweenAmount, crossfadeWeights, dragSettle, labelSlots, selectedIndex, STEP_DEG, stepSpring, wheelGeometry, wheelSettle,
} from "./recordWheel";

describe("selectedIndex", () => {
  it("is the nearest song, looping round", () => {
    expect(selectedIndex(0, 3)).toBe(0);
    expect(selectedIndex(0.49, 3)).toBe(0);
    expect(selectedIndex(0.51, 3)).toBe(1);
    expect(selectedIndex(2.6, 3)).toBe(0);
    expect(selectedIndex(-1, 3)).toBe(2);
    expect(selectedIndex(-4.2, 3)).toBe(2);
  });
});

describe("crossfadeWeights", () => {
  it("shows only the selected song at rest", () => {
    expect(crossfadeWeights(1, 3)).toEqual([0, 1, 0]);
  });
  it("blends the two neighbours in between", () => {
    const w = crossfadeWeights(0.25, 3);
    expect(w[0]).toBeCloseTo(0.75);
    expect(w[1]).toBeCloseTo(0.25);
    expect(w[2]).toBeCloseTo(0);
  });
  it("blends across the loop from the last song to the first", () => {
    const w = crossfadeWeights(2.5, 3);
    expect(w[2]).toBeCloseTo(0.5);
    expect(w[0]).toBeCloseTo(0.5);
  });
  it("always sums to one", () => {
    for (const u of [-3.7, -1, -0.2, 0, 0.3, 1.5, 2.99, 7.25]) {
      for (const n of [1, 2, 3, 4]) {
        expect(crossfadeWeights(u, n).reduce((a, b) => a + b, 0)).toBeCloseTo(1);
      }
    }
  });
});

describe("betweenAmount", () => {
  it("is 0 on a song and 1 halfway between two", () => {
    expect(betweenAmount(2)).toBe(0);
    expect(betweenAmount(0.5)).toBe(1);
    expect(betweenAmount(0.25)).toBeCloseTo(0.5);
    expect(betweenAmount(1.9)).toBeCloseTo(0.2);
  });
});

describe("labelSlots", () => {
  const g = { cx: 500, cy: 400, rn: 300 };

  it("shows three songs at rest: the selected one at the needle, one above, one below", () => {
    const s = labelSlots(0, 3, g);
    expect(s.map((x) => x.key)).toEqual([-1, 0, 1]);
    const [above, sel, below] = s;
    expect(sel).toMatchObject({ song: 0, selected: true, angleDeg: 180, scale: 1, opacity: 1 });
    expect(sel.x).toBeCloseTo(200);
    expect(sel.y).toBeCloseTo(400);
    expect(above.song).toBe(2);
    expect(above.y).toBeLessThan(400);
    expect(below.y).toBeGreaterThan(400);
    expect(above.angleDeg).toBe(180 + STEP_DEG);
    expect(below.scale).toBeCloseTo(0.78);
    expect(below.opacity).toBeCloseTo(0.6);
  });
  it("never shows more than four, and the ones leaving fade out", () => {
    for (const u of [0.1, 0.5, 0.9, 1.4]) {
      const s = labelSlots(u, 5, g);
      expect(s.length).toBeLessThanOrEqual(4);
      for (const x of s) if (Math.abs(x.key - u) > 1) expect(x.opacity).toBeLessThan(0.6);
    }
  });
  it("selects exactly one", () => {
    expect(labelSlots(0.6, 3, g).filter((x) => x.selected).map((x) => x.key)).toEqual([1]);
  });
});

describe("wheelGeometry", () => {
  it("puts a record about 1.1 screen-heights across just inside the right edge", () => {
    const g = wheelGeometry(1440, 900, 1440 * 0.48, 0);
    expect(g.R).toBeCloseTo(504);
    expect(g.rl).toBeCloseTo(221.76);
    expect(g.rn).toBeCloseTo(344.88);
    expect(g.cy).toBe(450);
    expect(g.discLeft).toBeCloseTo(704.16);
  });
});

describe("settling", () => {
  it("snaps back after a tiny wheel nudge", () => {
    expect(wheelSettle(0, 0.1)).toBe(0);
  });
  it("moves at least one song after a short swipe", () => {
    expect(wheelSettle(0, 0.3)).toBe(1);
    expect(wheelSettle(0, -0.13)).toBe(-1);
  });
  it("moves several songs after a long swipe", () => {
    expect(wheelSettle(0, 2.4)).toBe(2);
    expect(wheelSettle(3, 1.2)).toBe(1);
  });
  it("carries a drag's speed into the settle", () => {
    expect(dragSettle(0.4, 2)).toBe(1);
    expect(dragSettle(0.4, 0)).toBe(0);
  });
  it("springs onto the target and stops", () => {
    let st = { u: 0, v: 0, done: false };
    let frames = 0;
    while (!st.done && frames < 600) {
      st = stepSpring(st, 2, 1 / 60);
      frames++;
    }
    expect(st.done).toBe(true);
    expect(st.u).toBe(2);
    expect(frames).toBeLessThan(120);
  });
});
