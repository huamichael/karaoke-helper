/**
 * The record control: start and stop, with a live level meter while recording.
 *
 * Shared by the line screen and Word practice. While recording, a ring pulses with
 * the input level and a thin bar shows the time used out of the limit; both are
 * written straight to the DOM every frame, so recording never re-renders React.
 *
 * Owner: A. Spec: docs/tasks/frontend.md ("Recording"), docs/design/ui.md §5.3.
 */
import { useEffect, useRef, type CSSProperties } from "react";
import { MicIcon, StopIcon } from "./icons";

export type Meter = { level(): number; elapsedMs(): number; limitMs: number };

type Props = {
  label: string;
  recording: boolean;
  primary: boolean;
  disabled?: boolean;
  meter: Meter | null;
  onClick(): void;
  style?: CSSProperties;
};

const fmt = (ms: number) => `0:${String(Math.floor(ms / 1000)).padStart(2, "0")}`;

export function RecordButton({ label, recording, primary, disabled, meter, onClick, style }: Props) {
  const btn = useRef<HTMLButtonElement>(null);
  const time = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!recording || !meter) return;
    let raf = requestAnimationFrame(function frame() {
      const el = btn.current;
      if (el) {
        el.style.setProperty("--v", meter.level().toFixed(3));
        el.style.setProperty("--t", Math.min(1, meter.elapsedMs() / meter.limitMs).toFixed(4));
      }
      if (time.current) time.current.textContent = fmt(meter.elapsedMs());
      raf = requestAnimationFrame(frame);
    });
    return () => cancelAnimationFrame(raf);
  }, [recording, meter]);

  return (
    <button
      ref={btn}
      className={`rec${primary || recording ? "" : " plain"}`}
      disabled={disabled}
      onClick={onClick}
      aria-label={recording ? "Stop recording" : undefined}
      style={style}
    >
      <span className="vol" />
      {recording ? <StopIcon /> : <MicIcon />}
      {label}
      {recording && (
        <>
          <span className="rec-time" ref={time}>0:00</span>
          <span className="bar"><i /></span>
        </>
      )}
    </button>
  );
}
