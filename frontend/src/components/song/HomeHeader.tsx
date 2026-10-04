/**
 * The song screen's header: the wordmark, one line on what the app does, and the
 * four steps. Under each step's number is one of the four grades, good to missing,
 * drawn like the subtitle's grade bars, so the steps double as their legend.
 * (Sound on and off is the cap on the tonearm's pivot: SoundCap.)
 *
 * Owner: A. Spec: docs/design/ui.md §4.1, §5.1.
 */
import type { CSSProperties } from "react";
import { Vinyl } from "../Vinyl";

const STEPS = [
  ["Listen to a line", "good"],
  ["Sing it back", "ok"],
  ["See every word", "wrong"],
  ["Practice the ones you missed", "missing"],
] as const;

export function HomeHeader() {
  return (
    <header className="h-top">
      <div>
        <div className="wordmark"><Vinyl />Lotus Roots</div>
        <p className="h-tag">Learn Mandarin by singing the songs you love.</p>
        <ol className="steps">
          {STEPS.map(([label, status], i) => (
            <li key={label} style={{ "--i": i } as CSSProperties}>
              <b className={`s-${status}`}>{i + 1}<i className="mark" aria-hidden /></b>{label}
            </li>
          ))}
        </ol>
      </div>
    </header>
  );
}
