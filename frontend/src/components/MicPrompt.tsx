/**
 * The microphone setup, inside the dock (first Record only). No window.
 *
 * Ask: "Recording needs your microphone", Allow microphone, Use a simulated mic, ✕.
 * Test: a live level meter with "Say 你好 (nǐ hǎo) to test it" (a green check once
 * sound is heard) and Start recording. Nothing is sent.
 *
 * Owner: A. Spec: docs/design/ui.md §5.2.
 */
import { useEffect, useRef, useState, type CSSProperties } from "react";
import type { Mic } from "../audio/recorder";
import { CheckIcon, CloseIcon, MicIcon } from "./icons";

export type MicPromptState = { stage: "ask" | "test"; error: string | null };

const s = (i: number) => ({ "--i": i }) as CSSProperties;

type Props = {
  state: MicPromptState;
  mic: Mic | null;
  onAllow(): void;
  onSimulate(): void;
  onStart(): void;
  onCancel(): void;
};

export function MicPrompt({ state, mic, onAllow, onSimulate, onStart, onCancel }: Props) {
  const bar = useRef<HTMLElement>(null);
  const [heard, setHeard] = useState(false);

  useEffect(() => {
    if (state.stage !== "test" || !mic) return;
    let raf = requestAnimationFrame(function frame() {
      const v = mic.level();
      if (bar.current) bar.current.style.width = `${v * 100}%`;
      if (!mic.simulated && v > 0.25) setHeard(true);
      raf = requestAnimationFrame(frame);
    });
    return () => cancelAnimationFrame(raf);
  }, [state.stage, mic]);

  const cancel = <button className="round" style={s(3)} onClick={onCancel} aria-label="Cancel"><CloseIcon /></button>;

  if (state.stage === "ask")
    return (
      <>
        <span className="mic-ask" style={s(0)}><MicIcon /><span>{state.error ?? "Recording needs your microphone."}</span></span>
        <button className="btn primary" style={s(1)} onClick={onAllow}>Allow microphone</button>
        <button className="btn quiet" style={s(2)} onClick={onSimulate}>Use a simulated mic</button>
        {cancel}
      </>
    );

  return (
    <>
      <span className="mic-ask" style={s(0)}>
        <span className="dmeter"><i ref={bar} /></span>
        {mic?.simulated ? <span>Using a simulated mic.</span>
          : heard ? <span className="ok inline-flex items-center gap-2"><CheckIcon />Got it. Your mic works.</span>
          : <span>Say 你好 (nǐ hǎo) to test it.</span>}
      </span>
      <button className="btn primary" style={s(1)} onClick={onStart} autoFocus>Start recording</button>
      {cancel}
    </>
  );
}
