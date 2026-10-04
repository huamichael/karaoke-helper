/**
 * Word practice: its states and the list of graded attempts.
 *
 * ready → (playing) → recording → grading → result | success, plus failed (the
 * recording is kept for Send again). Success comes only from the returned word's
 * status being "good". Attempts live in memory for the session only.
 *
 * Owner: A. Spec: docs/design/ui.md §5.4 and §7, rule 1.
 */
import type { AttemptResult, Status } from "../api/client";

export const NO_SPEECH_WORD = "We didn't hear anything. Say the word a little louder.";

export type PracticePhase = "ready" | "playing" | "recording" | "grading" | "result" | "success" | "failed";

export type Practice = {
  lineIndex: number;
  wordIndex: number;
  phase: PracticePhase;
  /** One status per graded attempt, oldest first: the dots beside the gloss. */
  attempts: Status[];
  last: AttemptResult | null;
  note: string | null;
  pending: Blob | null;
};

export type PracticeEvent =
  | { type: "listen" }
  | { type: "listenEnd" }
  | { type: "record" }
  | { type: "recorded"; audio: Blob }
  | { type: "cancelRecording" }
  | { type: "graded"; result: AttemptResult }
  | { type: "failed"; message: string }
  | { type: "resend" }
  | { type: "keep" };

export function openPractice(lineIndex: number, wordIndex: number): Practice {
  return { lineIndex, wordIndex, phase: "ready", attempts: [], last: null, note: null, pending: null };
}

/** The practiced word's status in a result, or null when nothing was graded. */
export function wordStatus(result: AttemptResult, wordIndex: number): Status | null {
  if (result.status !== "ok" || !result.words.length) return null;
  return (result.words.find((w) => w.index === wordIndex) ?? result.words[0]).status;
}

/** Clicking the faded lyrics ends practice, but not while recording or grading. */
export const canLeave = (p: Practice) => p.phase !== "recording" && p.phase !== "grading";

/** The practiced ✓ is earned once any attempt came back good. */
export const earnedMark = (p: Practice) => p.attempts.includes("good");

const rest = (p: Practice): PracticePhase => (p.last ? "result" : "ready");

export function practiceReducer(p: Practice, e: PracticeEvent): Practice {
  switch (e.type) {
    case "listen":
      return ["ready", "result", "failed"].includes(p.phase) ? { ...p, phase: "playing", note: null, pending: null } : p;
    case "listenEnd":
      return p.phase === "playing" ? { ...p, phase: rest(p) } : p;
    case "record":
      return ["ready", "result", "playing", "success"].includes(p.phase) ? { ...p, phase: "recording", note: null } : p;
    case "recorded":
      return p.phase === "recording" ? { ...p, phase: "grading", pending: e.audio } : p;
    case "cancelRecording":
      return p.phase === "recording" ? { ...p, phase: rest(p) } : p;
    case "graded": {
      if (p.phase !== "grading") return p;
      const st = wordStatus(e.result, p.wordIndex);
      if (e.result.status === "no_speech" || !st) return { ...p, phase: "ready", last: null, note: NO_SPEECH_WORD, pending: null };
      return { ...p, phase: st === "good" ? "success" : "result", attempts: [...p.attempts, st], last: e.result, note: null, pending: null };
    }
    case "failed":
      return p.phase === "grading" ? { ...p, phase: "failed", note: e.message } : p;
    case "resend":
      return p.phase === "failed" && p.pending ? { ...p, phase: "grading", note: null } : p;
    case "keep":
      return p.phase === "success" ? { ...p, phase: "result" } : p;
  }
}
