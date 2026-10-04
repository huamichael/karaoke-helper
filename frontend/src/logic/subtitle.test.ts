import { describe, expect, it } from "vitest";
import { previewWindow, subtitleIndex } from "./subtitle";

const at = (start_ms: number, end_ms: number) => ({ start_ms, end_ms });

describe("subtitleIndex", () => {
  const lines = [at(1000, 2000), at(2000, 3000), at(8000, 9000)];

  it("shows the first line, waiting, before the song reaches it", () => {
    expect(subtitleIndex(lines, 0)).toBe(0);
  });
  it("shows the line being sung", () => {
    expect(subtitleIndex(lines, 1500)).toBe(0);
    expect(subtitleIndex(lines, 2500)).toBe(1);
  });
  it("moves straight on when the next line follows without a gap", () => {
    expect(subtitleIndex(lines, 2000)).toBe(1);
  });
  it("holds a finished line a moment before showing the next one, waiting", () => {
    expect(subtitleIndex(lines, 3400)).toBe(1);
    expect(subtitleIndex(lines, 3700)).toBe(2);
  });
  it("shows the next line a little before it starts when the gap is short", () => {
    const close = [at(0, 1000), at(1300, 2000)];
    expect(subtitleIndex(close, 900)).toBe(0);
    expect(subtitleIndex(close, 1000)).toBe(1);
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
