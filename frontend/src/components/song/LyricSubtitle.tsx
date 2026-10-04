/**
 * The song screen's subtitle: at the bottom, like a film subtitle, the lyric of
 * the song on the record, one line at a time, in time with the track. Each
 * character fills left to right as it is sung, with the line screen's karaoke
 * fill (logic/timing.ts: each syllable's own time once the track is aligned,
 * else the line split evenly); logic/subtitle.ts picks the line. Once a character
 * is sung, a status bar grows in under it, as if the singer were being graded:
 * pretend grades (demoMarks), not a result. A new line rises in out of a blur as
 * the last one drifts up and away.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("The subtitle").
 */
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import type { Line } from "../../api/client";
import { demoMarks, subtitleIndex } from "../../logic/subtitle";
import { fillFractions } from "../../logic/timing";

type Props = {
  songId: string;
  lines: Line[];
  /** The track position in ms while the record plays, else null (the subtitle then rests). */
  timeMs(): number | null;
};

const EASE = [0.2, 0.8, 0.2, 1] as const;
const same = (a: number[], b: number[]) => a.length === b.length && a.every((x, i) => Math.abs(x - b[i]) < 0.004);

export function LyricSubtitle({ songId, lines, timeMs }: Props) {
  const [view, setView] = useState<{ index: number; fill: number[] }>({ index: 0, fill: [] });
  const read = useRef(timeMs);
  read.current = timeMs;

  // A new song starts on its first line, waiting.
  useEffect(() => { setView({ index: 0, fill: [] }); }, [songId]);

  useEffect(() => {
    let raf = requestAnimationFrame(function frame() {
      const t = read.current();
      if (t != null && lines.length) {
        const index = subtitleIndex(lines, t);
        const fill = fillFractions(lines[index], t);
        setView((v) => (v.index === index && same(v.fill, fill) ? v : { index, fill }));
      }
      raf = requestAnimationFrame(frame);
    });
    return () => cancelAnimationFrame(raf);
  }, [lines]);

  const line = lines[view.index];
  const marks = useMemo(() => demoMarks(songId, view.index, line?.syllables.length ?? 0), [songId, view.index, line]);
  if (!line) return null;
  return (
    <div className="subtitle" aria-hidden>
      <div className="sub-lines">
        <AnimatePresence initial={false}>
          <motion.div
            key={`${songId}:${view.index}`}
            className="sub-line"
            initial={{ opacity: 0, y: 18, filter: "blur(6px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -18, filter: "blur(6px)" }}
            transition={{ duration: 0.55, ease: EASE }}
          >
            {line.syllables.map((s, j) => {
              const f = view.fill[j] ?? 0;
              return (
                <span className={`tok s-${marks[j]}${f >= 0.999 ? " graded" : ""}`} key={j}>
                  <span className="py">{s.pinyin}</span>
                  <span className="hz" data-hz={s.hanzi} style={{ "--f": f } as CSSProperties}>{s.hanzi}</span>
                  <i className="mark" />
                </span>
              );
            })}
          </motion.div>
        </AnimatePresence>
      </div>
      <p className="sub-cap">Sing a line back and every word gets a colour.</p>
    </div>
  );
}
