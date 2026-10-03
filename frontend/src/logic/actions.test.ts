import { describe, expect, it } from "vitest";
import type { NextStep } from "../api/client";
import { actionsFor, type DockAction, type LinePhase } from "./actions";

const NEXT: NextStep = { type: "next_line", message: "" };
const RETRY: NextStep = { type: "retry_line", message: "" };
const PRACTISE: NextStep = { type: "practice_word", word_index: 2, message: "" };
const ids = (a: DockAction[]) => a.map((x) => x.id);
const primary = (a: DockAction[]) => a.filter((x) => x.primary && x.kind !== "vinyl").map((x) => x.id);

describe("actionsFor, controls closed", () => {
  it("idle offers only Listen, on the vinyl", () => {
    const a = actionsFor("idle", null, false);
    expect(a).toEqual([expect.objectContaining({ id: "listen", kind: "vinyl", label: "Listen", disabled: false })]);
  });
  it("listening shows the vinyl as Playing", () => {
    expect(actionsFor("listening", null, false)).toEqual([expect.objectContaining({ id: "listen", label: "Playing" })]);
  });
  it("ready adds Record as the primary action", () => {
    const a = actionsFor("ready", null, false);
    expect(ids(a)).toEqual(["listen", "record"]);
    expect(a[0].label).toBeNull();
    expect(a[1]).toMatchObject({ kind: "record", label: "Record", primary: true });
  });
  it("recording disables the vinyl and turns Record into Stop", () => {
    const a = actionsFor("recording", null, false);
    expect(a[0].disabled).toBe(true);
    expect(a[1]).toMatchObject({ id: "record", label: "Stop", primary: true });
  });
  it("grading shows the busy state", () => {
    expect(ids(actionsFor("grading", null, false))).toEqual(["listen", "busy"]);
  });
  it("a result offers Retry and Next line, Next line primary", () => {
    const a = actionsFor("result", NEXT, false);
    expect(ids(a)).toEqual(["listen", "retry", "next"]);
    expect(a[1].kind).toBe("round");
    expect(a[2]).toMatchObject({ label: "Next line", primary: true });
  });
  it("practice_word keeps Next line primary", () => {
    expect(primary(actionsFor("result", PRACTISE, false))).toEqual(["next"]);
  });
  it("retry_line makes Retry the primary action", () => {
    const a = actionsFor("result", RETRY, false);
    expect(ids(a)).toEqual(["listen", "next", "retry"]);
    expect(primary(a)).toEqual(["retry"]);
    expect(a[2].label).toBe("Retry");
  });
  it("on the last line Next line reads Back to songs", () => {
    expect(actionsFor("result", NEXT, false, { last: true })[2].label).toBe("Back to songs");
  });
  it("a failed request offers Send again", () => {
    const a = actionsFor("failed", null, false);
    expect(ids(a)).toEqual(["listen", "resend"]);
    expect(a[1]).toMatchObject({ label: "Send again", primary: true });
  });
});

describe("actionsFor, controls open", () => {
  const phases: LinePhase[] = ["idle", "listening", "ready", "recording", "grading", "result", "failed"];

  it("always shows every control in the same order", () => {
    for (const p of phases) {
      const slots = ids(actionsFor(p, NEXT, true));
      expect(slots[0]).toBe("listen");
      expect(["record", "busy"]).toContain(slots[1]);
      expect(["retry", "resend"]).toContain(slots[2]);
      expect(slots[3]).toBe("next");
    }
  });
  it("labels the vinyl in every state", () => {
    expect(actionsFor("idle", null, true)[0].label).toBe("Listen");
    expect(actionsFor("listening", null, true)[0].label).toBe("Playing");
  });
  it("dims what is unavailable while recording", () => {
    const a = actionsFor("recording", null, true);
    expect(a.map((x) => x.disabled)).toEqual([true, false, true, true]);
  });
  it("Record is unavailable when idle", () => {
    expect(actionsFor("idle", null, true)[1]).toMatchObject({ id: "record", disabled: true, primary: false });
  });
  it("retry_line makes Retry primary, not Next line", () => {
    expect(primary(actionsFor("result", RETRY, true))).toEqual(["retry"]);
  });
  it("failed shows Send again in the retry slot", () => {
    expect(actionsFor("failed", null, true)[2]).toMatchObject({ id: "resend", label: "Send again", primary: true, disabled: false });
  });
});

describe("actionsFor, invariants", () => {
  it("never has more than one primary button", () => {
    const phases: LinePhase[] = ["idle", "listening", "ready", "recording", "grading", "result", "failed"];
    for (const p of phases) for (const step of [null, NEXT, RETRY, PRACTISE]) for (const open of [false, true]) {
      expect(primary(actionsFor(p, step, open)).length).toBeLessThanOrEqual(1);
    }
  });
});
