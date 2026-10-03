import { describe, expect, it } from "vitest";
import { fillFractions, notchPosition, recordLimitMs, wordLimitMs } from "./timing";

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
  it("follows each syllable's own time once aligned", () => {
    const aligned = {
      start_ms: 0, end_ms: 4000,
      syllables: [
        { ...LINE.syllables[0], start_ms: 0, end_ms: 1000 },
        { ...LINE.syllables[1], start_ms: 1500, end_ms: 2000 },
      ],
    };
    expect(fillFractions(aligned, 1750)).toEqual([1, 0.5]);
    expect(fillFractions(aligned, 1200)).toEqual([1, 0]);
  });
  it("falls back to the even split if any syllable is unaligned", () => {
    const partial = { start_ms: 0, end_ms: 2000, syllables: [{ ...LINE.syllables[0], start_ms: 0, end_ms: 100 }, LINE.syllables[1]] };
    expect(fillFractions(partial, 500)).toEqual([0.5, 0]);
  });
});
