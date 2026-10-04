/**
 * The song screen's subtitle: at the bottom, like a film subtitle, the lyric of
 * the song on the record, one line at a time, in time with the track. Each
 * character fills left to right as it is sung, with the line screen's karaoke
 * fill (logic/timing.ts: each syllable's own time once the track is aligned,
 * else the line split evenly); logic/subtitle.ts picks the line by that same fill,
 * so the next line has risen in before its first character is sung. Once a character
 * is sung, a status bar grows in under it, as if the singer were being graded:
 * pretend grades (demoMarks), not a result. A new line rises in out of a blur as
 * the last one drifts up and away.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("The subtitle").
 */
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Line } from "../../api/client";
import { demoMarks, subtitleIndex } from "../../logic/subtitle";
import { fillFractions, fillSpan } from "../../logic/timing";

type Props = {
  songId: string;
  lines: Line[];
  /** The track position in ms while the record plays, else null (the subtitle then rests). */
  timeMs(): number | null;
};

const EASE = [0.2, 0.8, 0.2, 1] as const;

/** One character's fill (its --f, 0 to 1), and its grade mark once it is sung. */
function paint(tok: HTMLElement, f: number) {
  const hz = tok.children[1] as HTMLElement | undefined, v = f.toFixed(3);
  if (hz && hz.style.getPropertyValue("--f") !== v) hz.style.setProperty("--f", v);
  tok.classList.toggle("graded", f >= 0.999);
}

export function LyricSubtitle({ songId, lines, timeMs }: Props) {
  const [index, setIndex] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const read = useRef(timeMs);
  read.current = timeMs;

  // A new song starts on its first line, waiting.
  useEffect(() => { setIndex(0); }, [songId]);

  // Which line shows goes by each line's fill (fillSpan), worked out once per song.
  const spans = useMemo(() => lines.map(fillSpan), [lines]);

  // Every frame: which line shows, rendered only when it changes, and how far each of its characters
  // has filled, written straight to them. A render a frame cost far more than the fill itself.
  useEffect(() => {
    let raf = requestAnimationFrame(function frame() {
      const t = read.current();
      if (t != null && lines.length) {
        const i = subtitleIndex(spans, t);
        setIndex(i);
        const toks = root.current?.querySelector(`.sub-line[data-k="${songId}:${i}"]`)?.children;
        if (toks) {
          const fill = fillFractions(lines[i], t);
          for (let j = 0; j < toks.length; j++) paint(toks[j] as HTMLElement, fill[j] ?? 0);
        }
      }
      raf = requestAnimationFrame(frame);
    });
    return () => cancelAnimationFrame(raf);
  }, [songId, lines, spans]);

  const line = lines[index];
  const marks = useMemo(() => demoMarks(songId, index, line?.syllables.length ?? 0), [songId, index, line]);
  if (!line) return null;
  return (
    <div ref={root} className="subtitle" aria-hidden>
      <div className="sub-lines">
        <AnimatePresence initial={false}>
          <motion.div
            key={`${songId}:${index}`}
            data-k={`${songId}:${index}`}
            className="sub-line"
            initial={{ opacity: 0, y: 18, filter: "blur(6px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -18, filter: "blur(6px)" }}
            transition={{ duration: 0.55, ease: EASE }}
          >
            {line.syllables.map((s, j) => (
              <span className={`tok s-${marks[j]}`} key={j}>
                <span className="py">{s.pinyin}</span>
                <span className="hz" data-hz={s.hanzi}>{s.hanzi}</span>
                <i className="mark" />
              </span>
            ))}
          </motion.div>
        </AnimatePresence>
      </div>
      <p className="sub-cap">Sing a line back and every word gets a colour.</p>
    </div>
  );
}
