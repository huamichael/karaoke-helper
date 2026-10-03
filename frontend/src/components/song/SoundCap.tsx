/**
 * Sound on and off is the cap on the tonearm's pivot, with a speaker icon (or M).
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("Sound").
 */
import { SoundOffIcon, SoundOnIcon } from "../icons";

export function SoundCap({ x, y, sound, onToggle }: { x: number; y: number; sound: boolean; onToggle(): void }) {
  const label = sound ? "Sound on" : "Sound off";
  return (
    <button className="arm-sound" style={{ left: x, top: y }} aria-pressed={sound} aria-label={label} title={`${label} (M)`} onClick={onToggle}>
      {sound ? <SoundOnIcon /> : <SoundOffIcon />}
    </button>
  );
}
