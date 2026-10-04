/**
 * The graded line: the lyric's own words are the chips.
 *
 * Each word shows its characters with Pinyin above (ruby style) and, once graded,
 * a status bar under it in its status colour and shape. Colour comes from the
 * word's status (good, ok, wrong, missing), never from a score. Clicking any word
 * of the active line opens Word practice for it.
 *
 * The word being practiced flies to the centre of the screen with Motion's
 * layoutId ("pword"); while it is there, its slot keeps an invisible copy so the
 * line does not move.
 *
 * Owner: A. Spec: docs/tasks/frontend.md (rules), docs/design/ui.md §5.3, §5.3.3, §5.4.
 */
import { motion } from "motion/react";
import type { CSSProperties, KeyboardEvent } from "react";
import type { AttemptResult, Line } from "../api/client";
import { phraseBreaks } from "../logic/phrases";
import { CheckIcon } from "./icons";
import { notchOffset, syllablesOf, WordTooltip } from "./WordTooltip";

type Props = {
  line: Line;
  active: boolean;
  result: AttemptResult | null;
  /** The result was just revealed: bars grow in, the suggested word pulses. */
  fresh: boolean;
  practiced: number[];
  /** Karaoke fill per syllable while the line plays. */
  fill: number[] | null;
  clickable: boolean;
  /** The word flying to or from the centre. */
  morphWord: number | null;
  /** The word sitting in the centre right now. */
  awayWord: number | null;
  onWord(index: number): void;
  onMorphDone(): void;
};

export function WordTokens({ line, syllables, fill }: { line: Line; syllables: number[]; fill?: number[] | null }) {
  return (
    <>
      {syllables.map((j) => {
        const s = line.syllables[j];
        return (
          <span className="tok" key={j}>
            <span className="py">{s.pinyin}</span>
            <span className="hz" data-hz={s.hanzi} style={fill ? ({ "--f": fill[j] ?? 0 } as CSSProperties) : undefined}>{s.hanzi}</span>
          </span>
        );
      })}
    </>
  );
}

export function WordChips({ line, active, result, fresh, practiced, fill, clickable, morphWord, awayWord, onWord, onMorphDone }: Props) {
  const suggest = active && result?.next_step.type === "practice_word" ? result.next_step.word_index : null;
  const breaks = active ? phraseBreaks(line) : [];
  return (
    <div className="words">
      {line.words.flatMap((w, k) => {
        const wr = result?.words.find((r) => r.index === w.index) ?? null;
        const status = wr?.status ?? null;
        const detail = result && wr && active ? syllablesOf(result, wr) : [];
        const notch = notchOffset(detail);
        const canClick = active && clickable;
        const cls = ["word", status && `s-${status}`, canClick && "clickable", suggest === k && "suggest", suggest === k && fresh && "pulse"]
          .filter(Boolean).join(" ");
        const tokens = <WordTokens line={line} syllables={w.syllable_indices} fill={fill} />;
        const core = awayWord === k
          ? <span className="wcore placeholder" aria-hidden>{tokens}</span>
          : morphWord === k
            ? <motion.span layoutId="pword" className="wcore" onLayoutAnimationComplete={onMorphDone}>{tokens}</motion.span>
            : <span className="wcore">{tokens}</span>;
        const open = (e: { stopPropagation(): void }) => { e.stopPropagation(); onWord(k); };
        const chip = (
          <span
            key={k}
            data-w={k}
            className={cls}
            role={canClick ? "button" : undefined}
            tabIndex={canClick ? 0 : -1}
            aria-label={canClick ? `Practice ${w.text}${status ? `, ${status}` : ""}` : undefined}
            onClick={canClick ? open : undefined}
            onKeyDown={canClick ? (e: KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(e); } } : undefined}
          >
            {core}
            <i
              key={result?.attempt_id ?? "none"}
              className={`mark${status ? " show" : ""}${fresh ? " fresh" : ""}${notch ? " notched" : ""}`}
              style={{ "--d": `${k * 0.06}s`, "--notch": notch ?? undefined } as CSSProperties}
            />
            {/* RHYTHM MARKER (disabled): "early" or "late" under the word in singing mode, separate
                from the chip colour, which is pronunciation only. Enable together with the backend
                field and regenerated types: docs/contracts/api.md, "Rhythm marker (disabled)".
            {active && wr?.rhythm && wr.rhythm !== "on_time" && (
              <span className={`rhythm r-${wr.rhythm}`}>{wr.rhythm === "early" ? "early" : "late"}</span>
            )} */}
            <span className="tip">Practice</span>
            {canClick && <WordTooltip syllables={detail} />}
            {practiced.includes(k) && <i className="chk" aria-hidden><CheckIcon /></i>}
          </span>
        );
        return breaks.includes(k) ? [chip, <span key={`br${k}`} className="row-break" aria-hidden />] : [chip];
      })}
    </div>
  );
}
