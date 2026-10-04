/**
 * The text under a result: the "what we heard" transcript, the feedback message,
 * and the suggested next step. All of it is rendered as sent by the backend.
 *
 * Under the line the message is next_step.message; in Word practice it is the
 * syllables' feedback.message (docs/design/ui.md §9, question 5).
 *
 * TODO(coach): docs/design/ui.md §5.5 shows this message as the coach speaking, in
 * a bubble (avatar 教 on glass) with "Ask why" opening a drawer, behind
 * VITE_SHOW_COACH (config.ts, SHOW_COACH). Not built: there is no coach endpoint yet.
 *
 * Owner: A. Spec: docs/tasks/frontend.md.
 */
import type { AttemptResult } from "../api/client";

export function Heard({ heard }: { heard: AttemptResult["heard"] }) {
  if (!heard) return null;
  return <p className="heard">We heard<span className="hh">{heard.hanzi}</span>{heard.pinyin}</p>;
}

export function Feedback({ message }: { message: string | null }) {
  if (!message) return null;
  return <p className="advice" role="status">{message}</p>;
}
