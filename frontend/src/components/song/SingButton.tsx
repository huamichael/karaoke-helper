/**
 * SingButton: one pill. Pressing Sing (or Enter) springs the same pill open into
 * Spoken accuracy, Singing accuracy and ✕, and a line under it explains whichever
 * option the pointer or focus is on. Choosing one starts the song.
 *
 * Singing accuracy shows, but until the backend's singing layers are on
 * (config.ts, SINGING_READY) choosing it only says it is not ready yet.
 *
 * Owner: A. Spec: docs/tasks/frontend.md ("Song screen"), docs/design/ui.md §5.1.
 */
import { useEffect, useRef, type CSSProperties } from "react";
import type { Mode } from "../../api/client";
import { CloseIcon } from "../icons";
import { MeasuredPill } from "../MeasuredPill";

export type ModeHint = Mode | "none" | "notReady";

export const MODE_HINT: Record<ModeHint, string> = {
  spoken: "Did the right words come out? Checks the sounds of each word.",
  singing: "A closer look at every sound, plus your rhythm against the original.",
  none: "You sing the same way in both. Pick how closely to grade you.",
  // TODO(backend): shown until singing accuracy is ready (config.ts, SINGING_READY).
  notReady: "Singing accuracy isn't ready yet. It's waiting for the backend.",
};

type Props = {
  title: string;
  singingReady: boolean;
  picking: boolean;
  onPicking(open: boolean): void;
  onHint(hint: ModeHint): void;
  onStart(mode: Mode): void;
};

export function SingButton({ title, singingReady, picking, onPicking, onHint, onStart }: Props) {
  const box = useRef<HTMLDivElement>(null);

  // A click anywhere else closes the choice.
  useEffect(() => {
    if (!picking) return;
    const off = (e: PointerEvent) => { if (!box.current?.contains(e.target as Node)) onPicking(false); };
    document.addEventListener("pointerdown", off);
    const t = setTimeout(() => box.current?.querySelector<HTMLElement>("[data-mode]")?.focus({ preventScroll: true }), 60);
    return () => { document.removeEventListener("pointerdown", off); clearTimeout(t); };
  }, [picking, onPicking]);

  const pick = (mode: Mode, i: number) => {
    const ready = mode === "spoken" || singingReady;
    return (
      <button data-mode={mode} className={ready ? undefined : "not-ready"} aria-disabled={!ready || undefined}
        style={{ "--i": i } as CSSProperties}
        onClick={() => (ready ? onStart(mode) : onHint("notReady"))}
        onMouseEnter={() => onHint(mode)} onFocus={() => onHint(mode)}>
        {mode === "spoken" ? "Spoken accuracy" : "Singing accuracy"}
      </button>
    );
  };

  return (
    <div ref={box}>
      <MeasuredPill className={`sing-pill${picking ? " picking" : ""}`} innerClassName="sing-inner" contentKey={picking ? "pick" : "go"} border={0}>
        {picking ? (
          <div className="sing-pick" role="group" aria-label="How should we grade you?">
            {pick("spoken", 0)}
            {pick("singing", 1)}
            <button className="sing-x" style={{ "--i": 2 } as CSSProperties} aria-label="Back" onClick={() => onPicking(false)}><CloseIcon /></button>
          </div>
        ) : (
          <button className="sing-go" onClick={() => { onHint("none"); onPicking(true); }}>Sing {title}</button>
        )}
      </MeasuredPill>
    </div>
  );
}
