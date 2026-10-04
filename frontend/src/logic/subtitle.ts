/**
 * The song screen's subtitle: the lyric of the song that is playing, one line at
 * a time, filling as the track plays (the line screen's karaoke fill, from
 * timing.ts). This module decides which line shows at a point in the track, and
 * which part of the track the record plays.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("The subtitle", "Preview").
 */

type Timed = { start_ms: number; end_ms: number };

/** A finished line stays this long before the next one shows, waiting. */
export const HOLD_MS = 600;
/** In a short gap, the next line shows this long before it starts. */
export const LEAD_MS = 500;
/** The preview starts this long before the first line and loops this long after the last. */
export const PAD_MS = 1500;

/** Which line shows at track time t: the one being sung, or the next one, waiting. -1 without lines. */
export function subtitleIndex(lines: Timed[], t: number): number {
  for (let i = 0; i < lines.length - 1; i++) {
    const end = lines[i].end_ms, next = lines[i + 1].start_ms;
    if (t < Math.max(end, Math.min(end + HOLD_MS, next - LEAD_MS))) return i;
  }
  return lines.length - 1;
}

/** The part of the track the record plays while the arm is down, looping: the whole lyric, padded. */
export function previewWindow(lines: Timed[]): { fromMs: number; toMs: number } {
  return { fromMs: Math.max(0, lines[0].start_ms - PAD_MS), toMs: lines[lines.length - 1].end_ms + PAD_MS };
}
