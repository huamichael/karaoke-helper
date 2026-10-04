/**
 * Word practice, in place (ui.md's WordPractice; no panel). Opened from any word.
 *
 * The clicked word moves to the exact centre of the screen (Motion layoutId
 * "pword", shared with WordChips) while the lyrics step back. The result is marked
 * on the word itself: each syllable's pinyin takes its status colour and underline,
 * and a caption under the character says what was heard. Under the word: its
 * meaning with one dot per graded attempt, every score that is not null, then a
 * hint, "Nailed it.", or one feedback message: the first syllable's that still
 * needs work. All of them at once ran under the dock in a word of two or three
 * syllables and hid the scores.
 *
 * Part has no status yet (ui.md §9, question 2), so the whole syllable is
 * coloured rather than its initial and final separately.
 *
 * Owner: A. Spec: docs/tasks/frontend.md ("Word practice panel"), docs/design/ui.md §5.4.
 */
import { motion } from "motion/react";
import type { Line, SyllableResult } from "../api/client";
import type { Practice } from "../logic/practiceMachine";
import { Feedback } from "./Feedback";
import { ScoreRow } from "./ScoreRow";

/** What was heard instead, read from the result's parts as sent. */
function caption(r: SyllableResult | null): string {
  if (!r || r.status === "good") return "";
  if (r.status === "missing") return "not heard";
  const off = [r.initial, r.final].find((p) => p && p.heard !== p.expected);
  const sound = off ? (off.heard ? `heard ${off.heard}` : "not heard") : "";
  const tone = r.tone && r.tone.heard != null && r.tone.heard !== r.tone.expected ? `tone ${r.tone.heard}` : "";
  return [sound, tone].filter(Boolean).join(", ");
}

export function WordPractice({ line, practice }: { line: Line; practice: Practice }) {
  const word = line.words[practice.wordIndex];
  const success = practice.phase === "success";
  const last = success ? null : practice.last;
  const wr = last?.words.find((w) => w.index === practice.wordIndex) ?? last?.words[0] ?? null;
  const resultFor = (k: number) => {
    const idx = wr?.syllable_indices[k];
    return idx == null ? null : last!.syllables.find((s) => s.index === idx) ?? null;
  };
  const message = last
    ? word.syllable_indices.map((_, k) => resultFor(k)?.feedback?.message).find(Boolean) ?? null
    : null;

  return (
    <div className={`focus${success ? " success" : ""}`} role="region" aria-label={`Practice ${word.text}`}>
      <div />
      <div className="f-mid">
        <motion.div layoutId="pword" className="f-word">
          {word.syllable_indices.map((j, k) => {
            const s = line.syllables[j], r = resultFor(k);
            const st = r && r.status !== "good" ? ` s-${r.status}` : "";
            return (
              <span className="tok" key={j}>
                <span className="py"><span className={`pp${st}`}>{s.pinyin}</span></span>
                <span className="hz">{s.hanzi}</span>
                <span className={`cap${r ? ` s-${r.status}` : ""}`}>{caption(r)}</span>
              </span>
            );
          })}
          <span className="burst" />
        </motion.div>
      </div>
      <div className="f-below">
        <p className="f-gloss">
          {word.gloss}
          {practice.attempts.length > 0 && (
            <span className="f-dots" aria-label="Your attempts">
              {practice.attempts.map((st, i) => <i key={i} className={`dot s-${st}`} />)}
            </span>
          )}
        </p>
        {practice.last && !practice.note && (
          <>
            {practice.last.engine === "mock" && <p className="f-note" role="status">Demo scores — your audio is not being graded.</p>}
            <ScoreRow key={practice.last.attempt_id} scores={practice.last.scores} fresh />
          </>
        )}
        {success ? <p className="f-status" role="status">Nailed it.</p>
          : practice.note ? <p className="f-note" role="status">{practice.note}</p>
          : !last ? <p className="f-hint">Listen, then say the word on its own.</p>
          : <Feedback message={message} />}
      </div>
    </div>
  );
}
