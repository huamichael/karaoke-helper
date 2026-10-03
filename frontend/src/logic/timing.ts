/**
 * Times the line screen needs: how long a recording may run, and how far the
 * karaoke fill has reached at a point in the track.
 *
 * Owner: A. Spec: docs/tasks/frontend.md ("Recording"), docs/design/ui.md §3.3 ("Karaoke fill").
 */
import type { Line, Syllable, Word } from "../api/client";

export const MAX_RECORD_MS = 30_000;
/** Saying one word takes a moment to start; never cut it off sooner than this. */
export const MIN_WORD_RECORD_MS = 5_000;

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const aligned = (ss: Syllable[]) => ss.length > 0 && ss.every((s) => s.start_ms != null && s.end_ms != null);

/** Stop automatically after twice the line's duration plus two seconds, never beyond 30 s. */
export function recordLimitMs(line: Pick<Line, "start_ms" | "end_ms">): number {
  return Math.min(MAX_RECORD_MS, 2 * (line.end_ms - line.start_ms) + 2_000);
}

/** The same rule for one word, using its sung length (aligned, or its share of the line). */
export function wordLimitMs(line: Line, word: Word): number {
  const ss = word.syllable_indices.map((i) => line.syllables[i]).filter(Boolean);
  const sung = aligned(ss)
    ? ss.reduce((t, s) => t + (s.end_ms! - s.start_ms!), 0)
    : ((line.end_ms - line.start_ms) / Math.max(1, line.syllables.length)) * ss.length;
  return Math.min(MAX_RECORD_MS, Math.max(MIN_WORD_RECORD_MS, Math.round(2 * sung + 2_000)));
}

/**
 * Where a word's early/late notch sits on its bar, in percent from the left: the
 * mean of its syllables' timing.offset_ms, 10 ms per percent, kept within 20–80%.
 * Null until the backend sends offsets. (ui.md §5.3.3, "Early or late")
 */
export function notchPosition(offsets: (number | null | undefined)[]): number | null {
  const offs = offsets.filter((x): x is number => x != null);
  if (!offs.length) return null;
  const mean = offs.reduce((a, b) => a + b, 0) / offs.length;
  return 50 + Math.max(-30, Math.min(30, mean / 10));
}

/**
 * How much of each syllable is filled at track time tMs, from 0 to 1. Uses each
 * syllable's start_ms and end_ms once the pipeline has aligned the track; until
 * then they are null, so the line's time is split evenly.
 */
export function fillFractions(line: Pick<Line, "start_ms" | "end_ms" | "syllables">, tMs: number): number[] {
  const ss = line.syllables;
  if (aligned(ss)) return ss.map((s) => clamp01((tMs - s.start_ms!) / Math.max(1, s.end_ms! - s.start_ms!)));
  const p = clamp01((tMs - line.start_ms) / Math.max(1, line.end_ms - line.start_ms));
  return ss.map((_, j) => clamp01(p * ss.length - j));
}
