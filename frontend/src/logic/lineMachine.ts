/**
 * The line screen's session: which line is active, its state, and every result.
 *
 * States: idle → listening → ready → recording → grading → result, plus failed
 * (the request failed; the recording is kept for Send again). no_speech returns
 * to ready with a message. Line changes are refused while recording or grading;
 * the caller also refuses them while a word is being practised.
 *
 * Owner: A. Spec: docs/tasks/frontend.md ("States of the line screen"), docs/design/ui.md §5.3, §7.
 */
import type { AttemptResult } from "../api/client";
import type { LinePhase } from "./actions";

export const NO_SPEECH_LINE = "We didn't hear anything. Move closer to the mic and sing again.";

export type Session = {
  lineIndex: number;
  lineCount: number;
  phase: LinePhase;
  /** The message under the line: no_speech or a failed request. */
  note: string | null;
  /** The recording being graded, kept until a result arrives so it can be sent again. */
  pending: Blob | null;
  /** Every result per line, newest last. In memory for the session only. */
  results: Record<number, AttemptResult[]>;
  /** Words whose practice ended after a good attempt, per line. */
  practised: Record<number, number[]>;
  /** The attempt whose result is being revealed right now (bars grow, scores count up). */
  fresh: string | null;
};

export type SessionEvent =
  | { type: "listen" }
  | { type: "listenEnd" }
  | { type: "record" }
  | { type: "recorded"; audio: Blob }
  | { type: "cancelRecording" }
  | { type: "graded"; result: AttemptResult }
  | { type: "failed"; message: string }
  | { type: "resend" }
  | { type: "goto"; index: number }
  | { type: "practised"; wordIndex: number }
  | { type: "singAgain" };

export function initSession(lineCount: number): Session {
  return { lineIndex: 0, lineCount, phase: "idle", note: null, pending: null, results: {}, practised: {}, fresh: null };
}

export function canChangeLine(s: Session, practising: boolean): boolean {
  return !practising && s.phase !== "recording" && s.phase !== "grading";
}

export function latestResult(s: Session, index = s.lineIndex): AttemptResult | null {
  const r = s.results[index];
  return r && r.length ? r[r.length - 1] : null;
}

export function sessionReducer(s: Session, e: SessionEvent): Session {
  const i = s.lineIndex;
  switch (e.type) {
    case "listen":
      return ["idle", "ready", "result", "failed"].includes(s.phase) ? { ...s, phase: "listening", note: null, pending: null } : s;
    case "listenEnd":
      return s.phase === "listening" ? { ...s, phase: "ready" } : s;
    case "record":
      return s.phase === "ready" || s.phase === "result" ? { ...s, phase: "recording", note: null } : s;
    case "recorded":
      return s.phase === "recording" ? { ...s, phase: "grading", pending: e.audio } : s;
    case "cancelRecording":
      return s.phase === "recording" ? { ...s, phase: "ready" } : s;
    case "graded": {
      if (s.phase !== "grading" || e.result.line_index !== i) return s;
      if (e.result.status === "no_speech") return { ...s, phase: "ready", note: NO_SPEECH_LINE, pending: null };
      return {
        ...s, phase: "result", note: null, pending: null, fresh: e.result.attempt_id,
        results: { ...s.results, [i]: [...(s.results[i] ?? []), e.result] },
        practised: { ...s.practised, [i]: [] },
      };
    }
    case "failed":
      return s.phase === "grading" ? { ...s, phase: "failed", note: e.message } : s;
    case "resend":
      return s.phase === "failed" && s.pending ? { ...s, phase: "grading", note: null } : s;
    case "goto":
      if (!canChangeLine(s, false) || e.index < 0 || e.index >= s.lineCount || e.index === i) return s;
      return { ...s, lineIndex: e.index, phase: "idle", note: null, pending: null, fresh: null };
    case "practised": {
      const done = s.practised[i] ?? [];
      return done.includes(e.wordIndex) ? s : { ...s, practised: { ...s.practised, [i]: [...done, e.wordIndex] } };
    }
    case "singAgain":
      return { ...s, phase: "ready", note: null, pending: null };
  }
}
