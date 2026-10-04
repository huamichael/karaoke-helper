/**
 * The song screen's subtitle: the lyric of the song that is playing, one line at
 * a time, filling as the track plays (the line screen's karaoke fill, from
 * timing.ts). This module decides which line shows at a point in the track, and
 * which part of the track the record plays.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("The subtitle", "Preview").
 */

type Timed = { start_ms: number; end_ms: number };
/** A line by its karaoke fill (timing.ts, fillSpan): its first character starts to fill, its last is full. */
type Fill = { fromMs: number; toMs: number };

/** A line stays this long after its last character is full before the next one shows, waiting. */
export const HOLD_MS = 600;
/** When the singing goes straight on, the next line shows this long before its first character fills, so
 *  it has risen in (0.55 s) by the time it is sung. A line still filling is never taken away for it. */
export const LEAD_MS = 500;
/** The preview starts this long before the first line and loops this long after the last. */
export const PAD_MS = 1500;

/**
 * Which line shows at track time t: the one being sung, or the next one, waiting. -1 without lines.
 * Goes by the fill, not the lines' start_ms and end_ms: an aligned line is sung, and full, well
 * before its end_ms, while the next often starts filling the moment it starts.
 */
export function subtitleIndex(lines: Fill[], t: number): number {
  for (let i = 0; i < lines.length - 1; i++) {
    const done = lines[i].toMs, next = lines[i + 1].fromMs;
    if (t < Math.max(done, Math.min(done + HOLD_MS, next - LEAD_MS))) return i;
  }
  return lines.length - 1;
}

/** A stable number in [0, 1) for a key (FNV-1a, then mixed). */
function unit(key: string): number {
  let h = 2166136261;
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  h ^= h >>> 13;
  h = Math.imul(h, 0x5bd1e995);
  h ^= h >>> 15;
  return (h >>> 0) / 4294967296;
}

/**
 * The subtitle's pretend grades: one status per character, like a singer who
 * mostly gets it right. About a quarter of the lines are all good; the rest have
 * one character off, yellow (ok) a little more often than red (wrong), in a
 * different place on each line. Decorative and fixed per song and line: nobody
 * is being graded, and nothing here is computed from a score.
 */
export function demoMarks(songId: string, line: number, count: number): ("good" | "ok" | "wrong")[] {
  const marks: ("good" | "ok" | "wrong")[] = new Array(count).fill("good");
  const kind = unit(`${songId}:${line}`);
  if (count && kind < 0.75) marks[Math.floor(unit(`${songId}:${line}:at`) * count)] = kind < 0.45 ? "ok" : "wrong";
  return marks;
}

/** The track time elapsedMs after the record started, going round the window again and again. */
export function loopTime(win: { fromMs: number; toMs: number }, elapsedMs: number): number {
  const span = win.toMs - win.fromMs;
  return span > 0 ? win.fromMs + (elapsedMs % span) : win.fromMs;
}

/** The part of the track the record plays while the arm is down, looping: the whole lyric, padded. */
export function previewWindow(lines: Timed[]): { fromMs: number; toMs: number } {
  return { fromMs: Math.max(0, lines[0].start_ms - PAD_MS), toMs: lines[lines.length - 1].end_ms + PAD_MS };
}
