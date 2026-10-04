import { describe, expect, it } from "vitest";
import { handoverMs, RUN_IN_MS, SKIP_LEAD_MS, startOf, waiting } from "./karaoke";
import { subtitleIndex } from "./subtitle";

// An intro, two lines sung straight on, a long break, and a last line.
const lines = [
  { fromMs: 20_000, toMs: 24_000 },
  { fromMs: 24_200, toMs: 28_000 },
  { fromMs: 45_000, toMs: 49_000 },
];

describe("startOf", () => {
  it("starts the first line with a run-in, never before the track", () => {
    expect(startOf(lines, 0)).toBe(20_000 - RUN_IN_MS);
    expect(startOf([{ fromMs: 1000, toMs: 2000 }], 0)).toBe(0);
  });
  it("never goes back so far that the line before still shows", () => {
    const at = startOf(lines, 1);
    expect(at).toBeGreaterThan(handoverMs(lines, 0));
    expect(subtitleIndex(lines, at)).toBe(1);
  });
  it("gives a line after a break its full run-in", () => {
    expect(startOf(lines, 2)).toBe(45_000 - RUN_IN_MS);
    expect(subtitleIndex(lines, startOf(lines, 2))).toBe(2);
  });
});

describe("waiting", () => {
  it("shows the intro and lets it be skipped to a few seconds before the first line", () => {
    expect(waiting(lines, 0, 5_000)).toEqual({ cue: "Instrumental · next line in 15 s", skipTo: 20_000 - SKIP_LEAD_MS });
  });
  it("counts in with dots over the last three seconds, which cannot be skipped", () => {
    expect(waiting(lines, 0, 17_500)).toEqual({ cue: "● ● ●", skipTo: null });
    expect(waiting(lines, 0, 19_200)).toEqual({ cue: "●", skipTo: null });
  });
  it("shows nothing once the line is being sung", () => {
    expect(waiting(lines, 0, 20_000)).toEqual({ cue: null, skipTo: null });
  });
  it("shows nothing between lines sung straight on", () => {
    expect(waiting(lines, 1, 23_900)).toEqual({ cue: null, skipTo: null });
  });
  it("shows a break between lines once the next line has taken over", () => {
    const t = handoverMs(lines, 1) + 1;
    expect(subtitleIndex(lines, t)).toBe(2);
    expect(waiting(lines, 2, t).cue).toMatch(/^Instrumental · next line in \d+ s$/);
    expect(waiting(lines, 2, t).skipTo).toBe(45_000 - SKIP_LEAD_MS);
  });
});
