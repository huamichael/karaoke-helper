import { describe, expect, it } from "vitest";
import { canChangeLine, initSession, latestResult, NO_SPEECH_LINE, sessionReducer, type Session, type SessionEvent } from "./lineMachine";
import { blob, lineResult, noSpeech } from "./testFixtures";

const run = (events: SessionEvent[], s: Session = initSession(3)) => events.reduce(sessionReducer, s);
const audio = blob();

describe("line session", () => {
  it("starts on line 1, idle", () => {
    expect(initSession(3)).toMatchObject({ lineIndex: 0, lineCount: 3, phase: "idle", note: null });
  });

  it("goes idle → listening → ready → recording → grading → result", () => {
    const events: SessionEvent[] = [
      { type: "listen" }, { type: "listenEnd" }, { type: "record" }, { type: "recorded", audio },
      { type: "graded", result: lineResult(["good", "ok", "wrong", "missing"]) },
    ];
    const phases: string[] = [];
    events.reduce((s, e) => { const n = sessionReducer(s, e); phases.push(n.phase); return n; }, initSession(3));
    expect(phases).toEqual(["listening", "ready", "recording", "grading", "result"]);
  });

  it("keeps every result for the line, newest last", () => {
    const a = lineResult(["wrong"]), b = lineResult(["good"]);
    const s = run([{ type: "listen" }, { type: "listenEnd" }, { type: "record" }, { type: "recorded", audio }, { type: "graded", result: a },
      { type: "record" }, { type: "recorded", audio }, { type: "graded", result: b }]);
    expect(s.results[0]).toEqual([a, b]);
    expect(latestResult(s)).toBe(b);
    expect(s.fresh).toBe(b.attempt_id);
  });

  it("no_speech says so and returns to ready without storing a result", () => {
    const s = run([{ type: "listen" }, { type: "listenEnd" }, { type: "record" }, { type: "recorded", audio }, { type: "graded", result: noSpeech() }]);
    expect(s.phase).toBe("ready");
    expect(s.note).toBe(NO_SPEECH_LINE);
    expect(s.results[0] ?? []).toEqual([]);
  });

  it("a failed request keeps the recording so it can be sent again", () => {
    const failed = run([{ type: "listen" }, { type: "listenEnd" }, { type: "record" }, { type: "recorded", audio }, { type: "failed", message: "No grader." }]);
    expect(failed).toMatchObject({ phase: "failed", note: "No grader.", pending: audio });
    const resent = sessionReducer(failed, { type: "resend" });
    expect(resent).toMatchObject({ phase: "grading", note: null, pending: audio });
  });

  it("drops the kept recording once a result arrives", () => {
    const s = run([{ type: "listen" }, { type: "listenEnd" }, { type: "record" }, { type: "recorded", audio }, { type: "graded", result: lineResult(["good"]) }]);
    expect(s.pending).toBeNull();
  });

  it("does not record from idle: listen first", () => {
    expect(run([{ type: "record" }]).phase).toBe("idle");
  });

  it("records again straight from a result", () => {
    const s = run([{ type: "listen" }, { type: "listenEnd" }, { type: "record" }, { type: "recorded", audio }, { type: "graded", result: lineResult(["good"]) }, { type: "record" }]);
    expect(s.phase).toBe("recording");
  });

  it("ignores a result for another line", () => {
    const s = run([{ type: "listen" }, { type: "listenEnd" }, { type: "record" }, { type: "recorded", audio }, { type: "graded", result: lineResult(["good"], undefined, 2) }]);
    expect(s.phase).toBe("grading");
  });

  it("changing line makes the new line idle and keeps the old results", () => {
    const r = lineResult(["good"]);
    const s = run([{ type: "listen" }, { type: "listenEnd" }, { type: "record" }, { type: "recorded", audio }, { type: "graded", result: r }, { type: "goto", index: 1 }]);
    expect(s).toMatchObject({ lineIndex: 1, phase: "idle", note: null, fresh: null });
    expect(s.results[0]).toEqual([r]);
  });

  it("refuses to change line while recording or grading", () => {
    const recording = run([{ type: "listen" }, { type: "listenEnd" }, { type: "record" }]);
    expect(canChangeLine(recording, false)).toBe(false);
    expect(sessionReducer(recording, { type: "goto", index: 1 }).lineIndex).toBe(0);
    const grading = sessionReducer(recording, { type: "recorded", audio });
    expect(sessionReducer(grading, { type: "goto", index: 1 }).lineIndex).toBe(0);
  });

  it("refuses to change line while a word is being practiced", () => {
    expect(canChangeLine(initSession(3), true)).toBe(false);
  });

  it("allows changing line while listening", () => {
    expect(run([{ type: "listen" }, { type: "goto", index: 1 }]).lineIndex).toBe(1);
  });

  it("stays put past the first or last line", () => {
    expect(run([{ type: "goto", index: -1 }]).lineIndex).toBe(0);
    expect(run([{ type: "goto", index: 3 }]).lineIndex).toBe(0);
  });

  it("marks a practiced word, and singing the line again clears the mark", () => {
    const practiced = run([{ type: "practiced", wordIndex: 2 }, { type: "practiced", wordIndex: 2 }]);
    expect(practiced.practiced[0]).toEqual([2]);
    const sung = run([{ type: "singAgain" }, { type: "record" }, { type: "recorded", audio }, { type: "graded", result: lineResult(["good"]) }], practiced);
    expect(sung.practiced[0]).toEqual([]);
  });

  it("Sing the line again puts the line in ready", () => {
    expect(run([{ type: "singAgain" }]).phase).toBe("ready");
  });

  it("cancelling the recording returns to ready", () => {
    expect(run([{ type: "listen" }, { type: "listenEnd" }, { type: "record" }, { type: "cancelRecording" }]).phase).toBe("ready");
  });
});
