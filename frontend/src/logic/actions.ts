/**
 * The dock's actions for each line-screen state.
 *
 * Closed, the dock holds only what the current step needs; open, it holds every
 * control with a label, dimming the unavailable ones. Exactly one button is the
 * primary (filled) one, chosen from the state and the backend's next_step.
 *
 * Owner: A. Spec: docs/design/ui.md §5.3 and §5.3.1.
 */
import type { NextStep } from "../api/client";

export type LinePhase = "idle" | "listening" | "ready" | "recording" | "grading" | "result" | "failed";

export type DockActionId = "listen" | "record" | "retry" | "resend" | "next" | "busy";

export type DockAction = {
  id: DockActionId;
  /** vinyl: the Listen record; record: the accent Record/Stop pill; round: an icon button; button: a labelled pill; busy: "Listening back…" */
  kind: "vinyl" | "record" | "round" | "button" | "busy";
  label: string | null;
  primary: boolean;
  disabled: boolean;
};

type Primary = "listen" | "record" | "retry" | "next" | null;

function primaryFor(phase: LinePhase, next: NextStep | null): Primary {
  if (phase === "result") return next?.type === "retry_line" ? "retry" : "next";
  return ({ idle: "listen", listening: null, ready: "record", recording: "record", grading: null, failed: "retry" } as const)[phase];
}

const act = (id: DockActionId, kind: DockAction["kind"], label: string | null, primary = false, disabled = false): DockAction => ({
  id, kind, label, primary, disabled,
});

export function actionsFor(phase: LinePhase, nextStep: NextStep | null, open: boolean, opts: { last?: boolean } = {}): DockAction[] {
  const primary = primaryFor(phase, nextStep);
  const nextLabel = opts.last ? "Back to songs" : "Next line";
  const busy = act("busy", "busy", "Listening back…");
  const recordLabel = phase === "recording" ? "Stop" : "Record";

  if (open) {
    const listenOk = ["idle", "listening", "ready", "result", "failed"].includes(phase);
    const recordSlot = phase === "grading" ? busy
      : act("record", "record", recordLabel, primary === "record", !["ready", "recording"].includes(phase));
    const retry = phase === "failed"
      ? act("resend", "button", "Send again", primary === "retry")
      : act("retry", "button", "Retry", primary === "retry", phase !== "result");
    return [
      act("listen", "vinyl", phase === "listening" ? "Playing" : "Listen", primary === "listen", !listenOk),
      recordSlot,
      retry,
      act("next", "button", nextLabel, primary === "next", phase === "recording" || phase === "grading"),
    ];
  }

  const vinyl = (label: string | null, disabled = false) => act("listen", "vinyl", label, primary === "listen", disabled);
  switch (phase) {
    case "idle": return [vinyl("Listen")];
    case "listening": return [vinyl("Playing")];
    case "ready": return [vinyl(null), act("record", "record", recordLabel, true)];
    case "recording": return [vinyl(null, true), act("record", "record", recordLabel, true)];
    case "grading": return [vinyl(null, true), busy];
    case "failed": return [vinyl(null), act("resend", "button", "Send again", true)];
    case "result":
      return primary === "retry"
        ? [vinyl(null), act("next", "button", nextLabel), act("retry", "button", "Retry", true)]
        : [vinyl(null), act("retry", "round", "Retry"), act("next", "button", nextLabel, true)];
  }
}
