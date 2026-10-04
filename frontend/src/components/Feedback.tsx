/**
 * The text under a result: the feedback message and the suggested next step,
 * rendered as sent by the backend. What the grader heard is not shown: its idea
 * of that can be mistaken, and a confident wrong diagnosis misleads more than it
 * helps (team decision, 4 October 2026; docs/contracts/scoring.md, "Feedback").
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

export function Feedback({ message }: { message: string | null }) {
  if (!message) return null;
  return <p className="advice" role="status">{message}</p>;
}
