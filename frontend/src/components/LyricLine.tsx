/**
 * Shows one lyric line: Hanzi with Pinyin for each character, and the translation.
 *
 * The active line is large and, under it, shows its latest result: the score row
 * and the feedback message (never what was heard: scoring.md, "Feedback"), then the
 * line's note (no_speech or a failed request). In Karaoke it shows the cue instead while the music plays on its
 * own before the line. Other lines are small and clickable to change line.
 *
 * Owner: A. Spec: docs/tasks/frontend.md, docs/design/ui.md §4.2, §5.3.
 */
import { memo, type CSSProperties } from "react";
import type { AttemptResult, Line } from "../api/client";
import type { LinePhase } from "../logic/actions";
import { Feedback } from "./Feedback";
import { ScoreRow } from "./ScoreRow";
import { WordChips } from "./WordChips";

type Props = {
  line: Line;
  index: number;
  activeIndex: number;
  phase: LinePhase;
  result: AttemptResult | null;
  fresh: boolean;
  practiced: number[];
  fill: number[] | null;
  note: string | null;
  /** Karaoke, during an instrumental break: "Instrumental · next line in 12 s", then a count-in. */
  cue?: string | null;
  /** Words can be clicked: not while recording, grading or practicing. */
  interactive: boolean;
  morphWord: number | null;
  awayWord: number | null;
  onWord(index: number): void;
  onLine(index: number): void;
  onMorphDone(): void;
};

/** Memoised: the screen passes inactive lines stable props, so a click or a state change re-renders only the active line. */
export const LyricLine = memo(function LyricLine({ line, index, activeIndex, phase, result, fresh, practiced, fill, note, cue = null, interactive, morphWord, awayWord, onWord, onLine, onMorphDone }: Props) {
  const active = index === activeIndex;
  const cls = ["line", active && "active", index < activeIndex && "past", active && fill && "filling", active && phase === "grading" && "grading"]
    .filter(Boolean).join(" ");
  return (
    <div className={cls} style={{ "--k": index } as CSSProperties} onClick={active ? undefined : () => onLine(index)}>
      <WordChips
        line={line}
        active={active}
        result={result}
        fresh={active && fresh}
        practiced={practiced}
        fill={active ? fill : null}
        clickable={interactive}
        morphWord={active ? morphWord : null}
        awayWord={active ? awayWord : null}
        onWord={onWord}
        onMorphDone={onMorphDone}
      />
      {active && (
        <div className="meta">
          {line.translation && <p className="tr">{line.translation}</p>}
          {cue && <p className={`cue${cue.startsWith("●") ? " count" : ""}`}>{cue}</p>}
          {result && (
            <div className="res">
              {result.engine === "mock" && <p className="note" role="status">Demo scores — your audio is not being graded.</p>}
              <ScoreRow scores={result.scores} fresh={fresh} />
              <Feedback message={result.next_step.message} />
            </div>
          )}
          {note && <p className="note" role="status">{note}</p>}
        </div>
      )}
    </div>
  );
});
