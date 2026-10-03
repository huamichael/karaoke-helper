import { describe, expect, it } from "vitest";
import { linearEasing, LINE_SPRING, SOFT_SPRING, sampleSpring } from "./spring";

describe("sampleSpring", () => {
  it("starts at 0 and ends exactly at 1", () => {
    const s = sampleSpring(210, 23);
    expect(s.points[0]).toBe(0);
    expect(s.points[s.points.length - 1]).toBe(1);
    expect(s.points.length).toBe(49);
  });
  it("the line spring overshoots a little and takes about half a second", () => {
    expect(Math.max(...LINE_SPRING.points)).toBeGreaterThan(1.005);
    expect(LINE_SPRING.durationMs).toBeGreaterThan(400);
    expect(LINE_SPRING.durationMs).toBeLessThan(750);
  });
  it("the soft spring barely overshoots and takes about 300ms", () => {
    expect(Math.max(...SOFT_SPRING.points)).toBeLessThan(1.001);
    expect(SOFT_SPRING.durationMs).toBeGreaterThan(250);
    expect(SOFT_SPRING.durationMs).toBeLessThan(500);
  });
});

describe("linearEasing", () => {
  it("writes a CSS linear() easing", () => {
    expect(linearEasing([0, 0.5, 1])).toBe("linear(0, 0.5, 1)");
  });
});
