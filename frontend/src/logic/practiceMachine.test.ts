import { describe, expect, it } from "vitest";
import { canLeave, earnedMark, NO_SPEECH_WORD, openPractice, practiceReducer, wordStatus, type Practice, type PracticeEvent } from "./practiceMachine";
import { blob, noSpeech, wordResult } from "./testFixtures";

const audio = blob();
const run = (events: PracticeEvent[], p: Practice = openPractice(0, 1)) => events.reduce(practiceReducer, p);
const attempt = (r: ReturnType<typeof wordResult>): PracticeEvent[] => [{ type: "record" }, { type: "recorded", audio }, { type: "graded", result: r }];

describe("word practice", () => {
  it("opens ready, with no attempts", () => {
    expect(openPractice(2, 3)).toMatchObject({ lineIndex: 2, wordIndex: 3, phase: "ready", attempts: [], last: null, note: null });
  });

  it("succeeds only when the word's status is good", () => {
    expect(run(attempt(wordResult("good"))).phase).toBe("success");
    for (const st of ["ok", "wrong", "missing"] as const) expect(run(attempt(wordResult(st))).phase).toBe("result");
  });

  it("keeps one dot per graded attempt", () => {
    const p = run([...attempt(wordResult("wrong")), ...attempt(wordResult("ok")), ...attempt(wordResult("good"))]);
    expect(p.attempts).toEqual(["wrong", "ok", "good"]);
  });

  it("no_speech asks for a louder try and adds no attempt", () => {
    const p = run(attempt(noSpeech("word")));
    expect(p).toMatchObject({ phase: "ready", note: NO_SPEECH_WORD, attempts: [] });
    const after = run(attempt(noSpeech("word")), run(attempt(wordResult("wrong"))));
    expect(after.phase).toBe("result");
  });

  it("listening returns to where it was", () => {
    expect(run([{ type: "listen" }, { type: "listenEnd" }]).phase).toBe("ready");
    expect(run([...attempt(wordResult("wrong")), { type: "listen" }, { type: "listenEnd" }]).phase).toBe("result");
  });

  it("a failed request keeps the recording for Send again", () => {
    const failed = run([{ type: "record" }, { type: "recorded", audio }, { type: "failed", message: "Offline." }]);
    expect(failed).toMatchObject({ phase: "failed", pending: audio, note: "Offline." });
    expect(practiceReducer(failed, { type: "resend" })).toMatchObject({ phase: "grading", pending: audio, note: null });
  });

  it("Keep practicing leaves the success state", () => {
    expect(run([...attempt(wordResult("good")), { type: "keep" }]).phase).toBe("result");
  });

  it("can record again after success", () => {
    expect(run([...attempt(wordResult("good")), { type: "record" }]).phase).toBe("recording");
  });

  it("earns the practiced mark once any attempt was good", () => {
    expect(earnedMark(run(attempt(wordResult("wrong"))))).toBe(false);
    expect(earnedMark(run([...attempt(wordResult("good")), ...attempt(wordResult("wrong"))]))).toBe(true);
  });

  it("cannot be left by clicking the lyrics while recording or grading", () => {
    expect(canLeave(run([{ type: "record" }]))).toBe(false);
    expect(canLeave(run([{ type: "record" }, { type: "recorded", audio }]))).toBe(false);
    expect(canLeave(run(attempt(wordResult("wrong"))))).toBe(true);
  });

  it("reads the status of the practiced word from the result", () => {
    expect(wordStatus(wordResult("ok", 3), 3)).toBe("ok");
    expect(wordStatus(noSpeech("word"), 1)).toBeNull();
  });
});
