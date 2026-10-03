/**
 * The song screen's title: Noto Serif SC 200, about 19% of the screen height, split
 * over two staggered lines (茉莉 / 花). Measured after rendering, its characters
 * (not the indent) shrink until every line ends at least 72px before the record.
 * The characters arrive one by one out of a blur, and drift away when a song starts.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("The title is the bold element").
 */
import { useLayoutEffect, useRef } from "react";
import type { Entry } from "../../logic/songList";

/** The theme's split, or halves for a title the theme does not know. */
export function titleLines(e: Entry): string[] {
  if (e.theme.split) return e.theme.split.filter((x): x is string => !!x);
  const chars = [...e.title];
  if (chars.length <= 2) return [e.title];
  const cut = Math.ceil(chars.length / 2);
  return [chars.slice(0, cut).join(""), chars.slice(cut).join("")];
}

export function SongTitle({ entry, avail, height }: { entry: Entry; avail: number; height: number }) {
  const h1 = useRef<HTMLHeadingElement>(null);
  const lines = titleLines(entry);

  useLayoutEffect(() => {
    const el = h1.current;
    if (!el) return;
    let ts = Math.floor(height * 0.19);
    el.style.setProperty("--ts", `${ts}px`);
    const fit = Math.min(1, ...[...el.children].map((l) => {
      const line = l as HTMLElement, pad = parseFloat(getComputedStyle(line).paddingLeft) || 0;
      return (avail - pad) / Math.max(1, line.offsetWidth - pad);
    }));
    if (fit < 1) ts = Math.floor(ts * fit);
    el.style.setProperty("--ts", `${ts}px`);
  }, [entry.id, avail, height]);

  let i = 0;
  return (
    <h1 ref={h1} className="h-title" aria-label={[entry.title, entry.theme.titleEnglish].filter(Boolean).join(", ")} key={entry.id}>
      {lines.map((line, k) => (
        <span className="h-line" key={k}>
          {[...line].map((c, j) => <span className="ch" key={j} style={{ ["--i" as string]: i++ }}>{c}</span>)}
        </span>
      ))}
    </h1>
  );
}
