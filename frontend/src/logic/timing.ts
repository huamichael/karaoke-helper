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

/** Each character starts filling this long before its syllable is sung, so the colour leads the voice. */
export const FILL_LEAD_MS = 80;
/** ...and is full within this long: about how long a sung syllable's sound lasts (the aligner's median is 280 ms). */
export const FILL_MAX_MS = 400;

/**
 * When each syllable starts in the track. The pipeline's aligned start_ms where it set one;
 * a syllable it missed is spaced evenly between its timed neighbours (or the line's own start
 * and end at the edges). Null when no syllable is aligned, as for a song not yet aligned.
 */
export function syllableStarts(line: Pick<Line, "start_ms" | "end_ms" | "syllables">): number[] | null {
  const ss = line.syllables;
  const known = ss.map((s) => (s.start_ms != null && s.start_ms >= line.start_ms && s.start_ms < line.end_ms ? s.start_ms : null));
  if (!known.some((x) => x != null)) return null;
  const starts = known.slice();
  if (starts[0] == null) starts[0] = line.start_ms;
  for (let i = 1; i < starts.length; i++) {
    if (starts[i] != null) continue;
    let j = i;
    while (j < starts.length && starts[j] == null) j++;
    const from = starts[i - 1]!;
    const to = j < starts.length ? starts[j]! : line.end_ms;
    const slots = j - i + 1;
    for (let k = i; k < j; k++) starts[k] = from + ((to - from) * (k - i + 1)) / slots;
    i = j - 1;
  }
  for (let i = 1; i < starts.length; i++) starts[i] = Math.max(starts[i]!, starts[i - 1]!);
  return starts as number[];
}

/**
 * How much of each syllable is filled at track time tMs, from 0 to 1.
 *
 * Once the pipeline has aligned the track, each character starts filling FILL_LEAD_MS before
 * its syllable is sung and is full FILL_MAX_MS after, or when the next syllable starts if that
 * comes first. A held note stays full while it is held, rather than filling slowly across it.
 * A line with no aligned syllable is split evenly.
 */
export function fillFractions(line: Pick<Line, "start_ms" | "end_ms" | "syllables">, tMs: number): number[] {
  const ss = line.syllables;
  const starts = syllableStarts(line);
  if (starts) {
    return starts.map((start, j) => {
      const next = j + 1 < starts.length ? starts[j + 1] : line.end_ms;
      const from = start - FILL_LEAD_MS;
      const to = Math.max(start, Math.min(next, start + FILL_MAX_MS));
      return clamp01((tMs - from) / Math.max(1, to - from));
    });
  }
  const p = clamp01((tMs - line.start_ms) / Math.max(1, line.end_ms - line.start_ms));
  return ss.map((_, j) => clamp01(p * ss.length - j));
}

/** When a line's first character starts to fill and when its last is full, by fillFractions' own rules. */
export function fillSpan(line: Pick<Line, "start_ms" | "end_ms" | "syllables">): { fromMs: number; toMs: number } {
  const starts = syllableStarts(line);
  if (!starts?.length) return { fromMs: line.start_ms, toMs: line.end_ms };
  const last = starts[starts.length - 1];
  return { fromMs: starts[0] - FILL_LEAD_MS, toMs: Math.max(last, Math.min(line.end_ms, last + FILL_MAX_MS)) };
}
