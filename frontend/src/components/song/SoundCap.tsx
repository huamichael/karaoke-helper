/**
 * Sound on and off is the cap on the tonearm's pivot, with a speaker icon (or M).
 * Its position and size come from the 3D cap projected to the screen (Tonearm),
 * so it stays centred on the cap at any window size, with an even ring of
 * polished metal round it. Hidden until the tonearm says where the cap is.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("Sound").
 */
import type { CapPlace } from "./Tonearm";

const stroke = { fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" } as const;
// viewBoxes nudged so each icon sits optically centred on the round cap
const On = () => <svg viewBox=".74 0 24 24" {...stroke}><path d="M4 9v6h4l5 4V5L8 9H4z" /><path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12" /></svg>;
const Off = () => <svg viewBox="1 0 24 24" {...stroke}><path d="M4 9v6h4l5 4V5L8 9H4z" /><path d="M17 9l5 6M22 9l-5 6" /></svg>;

export function SoundCap({ place, sound, onToggle }: { place: CapPlace | null; sound: boolean; onToggle(): void }) {
  const label = sound ? "Sound on" : "Sound off";
  return (
    <button className={`arm-sound${place ? " placed" : ""}`} style={place ? { left: place.x, top: place.y, width: place.d, height: place.d } : undefined}
      aria-pressed={sound} aria-label={label} title={`${label} (M)`} onClick={onToggle}>
      {sound ? <On /> : <Off />}
    </button>
  );
}
