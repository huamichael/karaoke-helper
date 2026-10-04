/**
 * Karaoke mode's timing. Which line shows is the song screen subtitle's rule
 * (logic/subtitle.ts, subtitleIndex) over each line's karaoke fill (timing.ts,
 * fillSpan). This module adds where the song goes when the singer jumps to a line,
 * and what shows while the music plays on its own before a line.
 *
 * Owner: A. Spec: docs/design/ui.md §5.6 ("Karaoke").
 */
import { HOLD_MS, LEAD_MS } from "./subtitle";

/** A line by its karaoke fill: its first character starts to fill, its last is full. */
type Fill = { fromMs: number; toMs: number };

/** Jumping to a line starts the song up to this long before the line, for a run-in. */
export const RUN_IN_MS = 3_000;
/** The music plays on its own for at least this long before a line (an intro or a break): show it. */
export const BREAK_MS = 4_000;
/** The count-in: one dot per second over this last stretch of a break. */
export const COUNT_MS = 3_000;
/** A break with more than this left can be skipped... */
export const SKIP_FROM_MS = 6_000;
/** ...to this long before the line, so the count-in still plays. */
export const SKIP_LEAD_MS = 3_000;

/** When line i+1 takes over from line i, by subtitleIndex's rule. */
export function handoverMs(lines: Fill[], i: number): number {
  const done = lines[i].toMs, next = lines[i + 1].fromMs;
  return Math.max(done, Math.min(done + HOLD_MS, next - LEAD_MS));
}

/** Where the song goes to sing line j: a short run-in, but never so early that the line before still shows. */
export function startOf(lines: Fill[], j: number): number {
  const runIn = lines[j].fromMs - RUN_IN_MS;
  // A few ms past the handover: the track reports its position a little short of where it was sent.
  return Math.max(0, j > 0 ? Math.max(handoverMs(lines, j - 1) + 20, runIn) : runIn);
}

export type Waiting = { cue: string | null; skipTo: number | null };
const NOT_WAITING: Waiting = { cue: null, skipTo: null };

/**
 * While line j shows but is not yet sung, at track time t: the cue under it during a
 * break ("Instrumental · next line in 12 s", then a count-in of dots) and, while
 * much of the break is left, where skipping it goes. Nothing between lines sung
 * straight on.
 */
export function waiting(lines: Fill[], j: number, t: number): Waiting {
  const from = lines[j].fromMs, left = from - t;
  const shownAt = j > 0 ? handoverMs(lines, j - 1) : 0;
  if (left <= 0 || from - shownAt < BREAK_MS) return NOT_WAITING;
  const seconds = Math.ceil(left / 1000);
  return {
    cue: left > COUNT_MS ? `Instrumental · next line in ${seconds} s` : Array(seconds).fill("●").join(" "),
    skipTo: left > SKIP_FROM_MS ? from - SKIP_LEAD_MS : null,
  };
}
