import { describe, expect, it } from "vitest";
import { demoMarks, HOLD_MS, LEAD_MS, loopTime, previewWindow, subtitleIndex } from "./subtitle";

describe("loopTime", () => {
  const win = { fromMs: 1000, toMs: 5000 };
  it("runs from the start of the window", () => {
    expect(loopTime(win, 0)).toBe(1000);
    expect(loopTime(win, 2500)).toBe(3500);
  });
  it("comes back round to the start, again and again", () => {
    expect(loopTime(win, 4000)).toBe(1000);
    expect(loopTime(win, 4500)).toBe(1500);
    expect(loopTime(win, 40_000 + 250)).toBe(1250);
  });
  it("copes with an empty window", () => {
    expect(loopTime({ fromMs: 800, toMs: 800 }, 1234)).toBe(800);
  });
});

describe("demoMarks", () => {
  it("gives one mark per character, the same every time", () => {
    const a = demoMarks("jasmine-flower", 3, 9);
    expect(a).toHaveLength(9);
    expect(demoMarks("jasmine-flower", 3, 9)).toEqual(a);
  });
  it("uses only good, ok and wrong", () => {
    for (let i = 0; i < 30; i++) for (const m of demoMarks("yi-jian-mei", i, 10)) expect(["good", "ok", "wrong"]).toContain(m);
  });
  it("marks at most one character of a line as off, like a singer who mostly gets it right", () => {
    for (const song of ["jasmine-flower", "yi-jian-mei", "yue-liang-dai-biao-wo-de-xin"])
      for (let i = 0; i < 26; i++) expect(demoMarks(song, i, 8).filter((m) => m !== "good").length).toBeLessThanOrEqual(1);
  });
  it("across a song, some lines are perfect, some have a yellow and some a red", () => {
    const lines = Array.from({ length: 26 }, (_, i) => demoMarks("yue-liang-dai-biao-wo-de-xin", i, 8));
    expect(lines.some((l) => l.every((m) => m === "good"))).toBe(true);
    expect(lines.some((l) => l.includes("ok"))).toBe(true);
    expect(lines.some((l) => l.includes("wrong"))).toBe(true);
  });
  it("puts the odd mark in different places on different lines", () => {
    const spots = new Set(Array.from({ length: 26 }, (_, i) => demoMarks("jasmine-flower", i, 9).findIndex((m) => m !== "good")).filter((k) => k >= 0));
    expect(spots.size).toBeGreaterThan(3);
  });
});

const at = (start_ms: number, end_ms: number) => ({ start_ms, end_ms });

// Each line by its fill (timing.ts, fillSpan): when its first character starts to fill, and when its last is full.
const fills = (fromMs: number, toMs: number) => ({ fromMs, toMs });

describe("subtitleIndex", () => {
  const lines = [fills(1000, 2000), fills(2000, 3000), fills(8000, 9000)];

  it("shows the first line, waiting, before the song reaches it", () => {
    expect(subtitleIndex(lines, 0)).toBe(0);
  });
  it("shows the line being sung", () => {
    expect(subtitleIndex(lines, 1500)).toBe(0);
    expect(subtitleIndex(lines, 2500)).toBe(1);
  });
  it("moves straight on when the next line fills right after", () => {
    expect(subtitleIndex(lines, 2000)).toBe(1);
  });
  it("holds a finished line a moment before showing the next one, waiting", () => {
    expect(subtitleIndex(lines, 3400)).toBe(1);
    expect(subtitleIndex(lines, 3700)).toBe(2);
  });
  it("shows the next line a little before it starts to fill when the gap is short", () => {
    const close = [fills(0, 1000), fills(1300, 2000)];
    expect(subtitleIndex(close, 900)).toBe(0);
    expect(subtitleIndex(close, 1000)).toBe(1);
  });
  it("goes by the fill: a line full early is held, then the next shows, waiting, long before it is sung", () => {
    const early = [fills(0, 1500), fills(3000, 5000)];
    expect(subtitleIndex(early, 1500 + HOLD_MS - 10)).toBe(0);
    expect(subtitleIndex(early, 1500 + HOLD_MS)).toBe(1);
  });
  it("cuts the hold short so the next line shows its whole lead before it fills", () => {
    const soon = [fills(0, 2200), fills(3000, 5000)];
    expect(subtitleIndex(soon, 3000 - LEAD_MS - 10)).toBe(0);
    expect(subtitleIndex(soon, 3000 - LEAD_MS)).toBe(1);
  });
  it("never takes a line away before it has finished filling", () => {
    const overlapping = [fills(0, 3000), fills(2800, 4000)];
    expect(subtitleIndex(overlapping, 2990)).toBe(0);
    expect(subtitleIndex(overlapping, 3000)).toBe(1);
  });
  it("stays on the last line after the song's last lyric", () => {
    expect(subtitleIndex(lines, 60_000)).toBe(2);
  });
  it("copes with a song without lines", () => {
    expect(subtitleIndex([], 500)).toBe(-1);
  });
});

describe("previewWindow", () => {
  it("starts a little before the first line and loops a little after the last", () => {
    expect(previewWindow([at(21_090, 26_730), at(26_730, 31_000)])).toEqual({ fromMs: 19_590, toMs: 32_500 });
  });
  it("never starts before the track does", () => {
    expect(previewWindow([at(500, 2000)]).fromMs).toBe(0);
  });
});
