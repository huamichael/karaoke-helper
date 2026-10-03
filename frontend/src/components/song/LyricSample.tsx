/**
 * The song screen's subtitle: at the bottom centre, like a film subtitle, one line
 * of the song fills and grades itself on a loop. Decorative: the marks are fixed
 * design data from the theme, not a result.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("The subtitle").
 */
import type { CSSProperties } from "react";
import type { SongTheme } from "../../theme/songThemes";

export function LyricSample({ sample }: { sample: SongTheme["sample"] }) {
  if (!sample) return null;
  const py = sample.py.split(" ");
  return (
    <div className="subtitle" aria-hidden key={sample.hz}>
      <div className="lyric-demo">
        {[...sample.hz].map((h, k) => (
          <div key={k} className={`tok s-${sample.marks[k] ?? "good"}`} style={{ "--d": `${(k * 0.3).toFixed(2)}s` } as CSSProperties}>
            <span className="py">{py[k]}</span>
            <span className="hz" data-hz={h}>{h}</span>
            <i className="mark" />
          </div>
        ))}
      </div>
      <p className="sub-cap">Sing a line back and every word gets a colour.</p>
    </div>
  );
}
