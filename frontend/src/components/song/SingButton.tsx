/**
 * SingButton: one pill. Pressing Sing (or Enter) springs the same pill open into
 * Practice mode, Karaoke mode and ✕, and a line under it explains whichever option
 * the pointer or focus is on. Choosing one starts the song.
 *
 * Practice mode grades every line and word (the API's spoken-accuracy grading).
 * Karaoke mode plays the instrumental with the lyrics in time and grades nothing.
 *
 * Owner: A. Spec: docs/tasks/frontend.md ("Song screen"), docs/design/ui.md §5.1.
 */
import { useEffect, useRef, type CSSProperties } from "react";
import { useWidthMorph } from "../../hooks/useWidthMorph";
import { CloseIcon } from "../icons";

export type PlayMode = "practice" | "karaoke";
export type ModeHint = PlayMode | "none";

export const MODE_NAME: Record<PlayMode, string> = { practice: "Practice mode", karaoke: "Karaoke mode" };

export const MODE_HINT: Record<ModeHint, string> = {
  practice: "Sing or say a line at a time and every word is graded. Click a word to practice it on its own.",
  karaoke: "Sing along to the instrumental, with the lyrics filling in time. Nothing is graded.",
  none: "Pick how you want to sing.",
};

type Props = {
  title: string;
  picking: boolean;
  onPicking(open: boolean): void;
  onHint(hint: ModeHint): void;
  onStart(mode: PlayMode): void;
};

export function SingButton({ title, picking, onPicking, onHint, onStart }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const pill = useRef<HTMLDivElement>(null);
  // Opening and closing spring the pill's width, a little slower than the dock, as in the prototype.
  useWidthMorph(pill, picking, 120);

  // A click anywhere else closes the choice.
  useEffect(() => {
    if (!picking) return;
    const off = (e: PointerEvent) => { if (!box.current?.contains(e.target as Node)) onPicking(false); };
    document.addEventListener("pointerdown", off);
    const t = setTimeout(() => box.current?.querySelector<HTMLElement>("[data-mode]")?.focus({ preventScroll: true }), 60);
    return () => { document.removeEventListener("pointerdown", off); clearTimeout(t); };
  }, [picking, onPicking]);

  const pick = (mode: PlayMode, i: number) => (
    <button data-mode={mode} style={{ "--i": i } as CSSProperties}
      onClick={() => onStart(mode)} onMouseEnter={() => onHint(mode)} onFocus={() => onHint(mode)}>
      {MODE_NAME[mode]}
    </button>
  );

  return (
    <div ref={box}>
      <div ref={pill} className={`sing-pill${picking ? " picking" : ""}`}>
        {picking ? (
          <div className="sing-pick" role="group" aria-label="How do you want to sing?">
            {pick("practice", 0)}
            {pick("karaoke", 1)}
            <button className="sing-x" style={{ "--i": 2 } as CSSProperties} aria-label="Back" onClick={() => onPicking(false)}><CloseIcon /></button>
          </div>
        ) : (
          <button className="sing-go" onClick={() => { onHint("none"); onPicking(true); }}>Sing {title}</button>
        )}
      </div>
    </div>
  );
}
