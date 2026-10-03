import { describe, expect, it } from "vitest";
import { armLayout, glyphPaths, PLATTER_SPEED, platterStep } from "./turntable";

describe("platterStep", () => {
  it("spins up towards the playing speed", () => {
    let s = 0;
    for (let i = 0; i < 120; i++) s = platterStep(s, PLATTER_SPEED, 1 / 60);
    expect(s).toBeGreaterThan(PLATTER_SPEED * 0.95);
    expect(s).toBeLessThanOrEqual(PLATTER_SPEED);
  });
  it("spins up faster than it slows down, like a heavy platter", () => {
    const up = platterStep(0, PLATTER_SPEED, 0.1);
    const down = PLATTER_SPEED - platterStep(PLATTER_SPEED, 0, 0.1);
    expect(up).toBeGreaterThan(down);
  });
  it("comes to a full stop instead of creeping forever", () => {
    let s = PLATTER_SPEED;
    for (let i = 0; i < 600 && s > 0; i++) s = platterStep(s, 0, 1 / 60);
    expect(s).toBe(0);
  });
  it("plays at 30° a second, calmer than a real 33⅓", () => {
    expect(PLATTER_SPEED).toBe(30);
  });
});

describe("glyphPaths", () => {
  it("draws the two pause bars at 0", () => {
    expect(glyphPaths(0)).toEqual(["M12.60 25.40 15.40 25.40 15.40 10.60 12.60 10.60z", "M20.60 25.40 23.40 25.40 23.40 10.60 20.60 10.60z"]);
  });
  it("draws the two halves of the play triangle at 1", () => {
    expect(glyphPaths(1)).toEqual(["M12.60 25.00 18.25 21.50 18.25 14.50 12.60 11.00z", "M18.25 21.50 23.90 18.00 23.90 18.00 18.25 14.50z"]);
  });
  it("folds the bars into the triangle point by point in between", () => {
    expect(glyphPaths(0.5)[0]).toBe("M12.60 25.20 16.82 23.45 16.82 12.55 12.60 10.80z");
  });
});

describe("armLayout", () => {
  // the record at 1440×900: R = 504 in a 691px-wide dial
  const g = { cx: 516.96, cy: 450, R: 504 };
  const a = armLayout(g, 691.2, 900);

  it("puts the pivot in the dial's top right", () => {
    expect(a.pivot).toEqual({ x: 691.2 - 72, y: 82 });
  });
  it("sets the stylus down on the record's lead-in at 190°, 0.86 of the radius", () => {
    const t = (190 * Math.PI) / 180;
    expect(a.leadIn.x).toBeCloseTo(g.cx + g.R * 0.86 * Math.cos(t));
    expect(a.leadIn.y).toBeCloseTo(g.cy + g.R * 0.86 * Math.sin(t));
    expect(a.length).toBeCloseTo(Math.hypot(a.leadIn.x - a.pivot.x, a.leadIn.y - a.pivot.y));
    expect(a.playAngle).toBeCloseTo(Math.atan2(a.leadIn.y - a.pivot.y, a.leadIn.x - a.pivot.x));
  });
  it("rests the arm along the top, off the record", () => {
    expect(a.restAngle).toBeCloseTo((184 * Math.PI) / 180);
    expect(a.rest.y).toBeLessThan(g.cy - g.R * 0.5);
  });
  it("lifts the stylus about 24px on the cue lever", () => {
    expect(a.lift * a.length).toBeCloseTo(24);
  });
});
