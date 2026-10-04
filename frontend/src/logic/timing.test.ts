import { describe, expect, it } from "vitest";
import { FILL_LEAD_MS, FILL_MAX_MS, fillFractions, fillSpan, syllableStarts, notchPosition, recordLimitMs, wordLimitMs } from "./timing";

describe("notchPosition", () => {
  it("has no notch until the backend sends offset_ms", () => {
    expect(notchPosition([null, null])).toBeNull();
    expect(notchPosition([])).toBeNull();
  });
  it("sits at the centre when on time", () => {
    expect(notchPosition([0])).toBe(50);
  });
  it("sits left of centre when early and right when late, by the word's mean offset", () => {
    expect(notchPosition([-120, null])).toBe(38);
    expect(notchPosition([100, 200])).toBe(65);
  });
  it("stays on the bar however far off", () => {
    expect(notchPosition([-5000])).toBe(20);
    expect(notchPosition([5000])).toBe(80);
  });
});
import { LINE } from "./testFixtures";

describe("recordLimitMs", () => {
  it("is twice the line plus two seconds", () => {
    expect(recordLimitMs({ start_ms: 1000, end_ms: 5000 })).toBe(10_000);
  });
  it("never exceeds 30 seconds", () => {
    expect(recordLimitMs({ start_ms: 0, end_ms: 20_000 })).toBe(30_000);
  });
});

describe("wordLimitMs", () => {
  it("gives a short word at least five seconds", () => {
    // 4000 ms over 8 syllables: a 2-syllable word is about 1000 ms, so 2 × 1000 + 2000 = 4000 → 5000
    expect(wordLimitMs(LINE, LINE.words[1])).toBe(5_000);
  });
  it("scales with a slowly sung word", () => {
    const slow = { ...LINE, end_ms: 32_000 }; // 4000 ms per syllable
    expect(wordLimitMs(slow, slow.words[1])).toBe(18_000);
  });
  it("uses the aligned syllable times when they are set", () => {
    const aligned = { ...LINE, syllables: LINE.syllables.map((s, i) => ({ ...s, start_ms: i * 3000, end_ms: i * 3000 + 2500 })) };
    // word 1 is syllables 2 and 3: 2500 + 2500 = 5000 → 2 × 5000 + 2000
    expect(wordLimitMs(aligned, aligned.words[1])).toBe(12_000);
  });
  it("never exceeds 30 seconds", () => {
    const huge = { ...LINE, end_ms: 400_000 };
    expect(wordLimitMs(huge, huge.words[0])).toBe(30_000);
  });
});

describe("fillFractions", () => {
  const four = { start_ms: 1000, end_ms: 5000, syllables: LINE.syllables.slice(0, 4) };

  it("is empty before the line starts", () => {
    expect(fillFractions(four, 0)).toEqual([0, 0, 0, 0]);
  });
  it("splits the line evenly when the track is not aligned", () => {
    expect(fillFractions(four, 3000)).toEqual([1, 1, 0, 0]);
    expect(fillFractions(four, 2500)).toEqual([1, 0.5, 0, 0]);
  });
  it("is full after the line ends", () => {
    expect(fillFractions(four, 9000)).toEqual([1, 1, 1, 1]);
  });
  const at = (i: number, start_ms: number | null, end_ms: number | null = start_ms == null ? null : start_ms + 100) =>
    ({ ...LINE.syllables[i], start_ms, end_ms });

  it("fills each aligned character quickly as its syllable is sung", () => {
    const line = { start_ms: 0, end_ms: 4000, syllables: [at(0, 1000), at(1, 2000), at(2, 3000)] };
    expect(fillFractions(line, 1000 - FILL_LEAD_MS)).toEqual([0, 0, 0]);
    expect(fillFractions(line, 1000 + FILL_MAX_MS)).toEqual([1, 0, 0]);
    const half = 1000 - FILL_LEAD_MS + (FILL_MAX_MS + FILL_LEAD_MS) / 2;
    expect(fillFractions(line, half)[0]).toBeCloseTo(0.5);
  });
  it("finishes a character by the time the next syllable starts", () => {
    const line = { start_ms: 0, end_ms: 4000, syllables: [at(0, 1000), at(1, 1200)] };
    expect(fillFractions(line, 1200)[0]).toBe(1);
  });
  it("keeps a held note full instead of filling slowly across it", () => {
    const line = { start_ms: 0, end_ms: 15000, syllables: [at(0, 0), at(1, 1000)] };
    expect(fillFractions(line, 1000 + FILL_MAX_MS)).toEqual([1, 1]);
    expect(fillFractions(line, 9000)).toEqual([1, 1]);
  });
  it("spaces a syllable the aligner missed between its timed neighbours", () => {
    const line = { start_ms: 0, end_ms: 4000, syllables: [at(0, 0), at(1, null), at(2, 2000)] };
    expect(syllableStarts(line)).toEqual([0, 1000, 2000]);
    expect(fillFractions(line, 1000 + FILL_MAX_MS)).toEqual([1, 1, 0]);
  });
  it("starts a leading missed syllable at the line start and spaces trailing ones to the line end", () => {
    const line = { start_ms: 1000, end_ms: 4000, syllables: [at(0, null), at(1, 2000), at(2, null)] };
    expect(syllableStarts(line)).toEqual([1000, 2000, 3000]);
  });
  it("ignores a start outside the line and keeps starts in order", () => {
    const line = { start_ms: 1000, end_ms: 4000, syllables: [at(0, 1000), at(1, 900), at(2, 2500), at(3, 2000)] };
    const starts = syllableStarts(line)!;
    expect(starts[1]).toBeGreaterThanOrEqual(starts[0]);
    expect(starts.every((s, i) => i === 0 || s >= starts[i - 1])).toBe(true);
  });
  it("splits the line evenly when no syllable is aligned", () => {
    expect(syllableStarts(four)).toBeNull();
    expect(fillFractions(four, 2500)).toEqual([1, 0.5, 0, 0]);
  });
});

describe("fillSpan", () => {
  const at = (i: number, start_ms: number) => ({ ...LINE.syllables[i], start_ms, end_ms: start_ms + 100 });
  const sung = { start_ms: 0, end_ms: 4000, syllables: [at(0, 1000), at(1, 2000), at(2, 3000)] };
  const even = { start_ms: 1000, end_ms: 5000, syllables: LINE.syllables.slice(0, 4) };

  it("runs from just before the first syllable is sung until the last one is full", () => {
    expect(fillSpan(sung)).toEqual({ fromMs: 1000 - FILL_LEAD_MS, toMs: 3000 + FILL_MAX_MS });
  });
  it("ends with the line when its last syllable is sung right at the end", () => {
    expect(fillSpan({ start_ms: 0, end_ms: 3200, syllables: [at(0, 1000), at(1, 3000)] }).toMs).toBe(3200);
  });
  it("is the line's own start and end when the track is not aligned", () => {
    expect(fillSpan(even)).toEqual({ fromMs: 1000, toMs: 5000 });
  });
  it("agrees with fillFractions: nothing filled at its start, everything full at its end and not before", () => {
    for (const line of [sung, even]) {
      const { fromMs, toMs } = fillSpan(line);
      expect(fillFractions(line, fromMs).every((f) => f === 0)).toBe(true);
      expect(fillFractions(line, fromMs + 10)[0]).toBeGreaterThan(0);
      expect(fillFractions(line, toMs).every((f) => f >= 0.999)).toBe(true);
      expect(fillFractions(line, toMs - 10).every((f) => f >= 0.999)).toBe(false);
    }
  });
});
