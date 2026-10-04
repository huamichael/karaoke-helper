/**
 * The cover is the record's play / stop switch, like a video player's.
 * Stopped: the label dims and shows ▶. Playing: nothing, until the pointer is on
 * it; then it dims and shows ⏸. The sign always shows what a click will do. On a
 * toggle the two pause bars fold into the two halves of the triangle in 240 ms.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("The cover works like a video player's play button").
 */
import { useEffect, useRef, useState, type MouseEvent } from "react";
import { glyphPaths } from "../../logic/turntable";

type Props = { cx: number; cy: number; rl: number; playing: boolean; onToggle(): void };

const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export function CoverButton({ cx, cy, rl, playing, onToggle }: Props) {
  // t: 0 = pause bars (shown while playing), 1 = play triangle (shown while stopped)
  const [t, setT] = useState(playing ? 0 : 1);
  const from = useRef(t);
  from.current = t;

  useEffect(() => {
    const to = playing ? 0 : 1, start = from.current, t0 = performance.now();
    if (reduced() || start === to) return setT(to);
    let raf = requestAnimationFrame(function frame(now) {
      const k = Math.min(1, (now - t0) / 240), e = 1 - Math.pow(1 - k, 3);
      setT(start + (to - start) * e);
      if (k < 1) raf = requestAnimationFrame(frame);
    });
    return () => cancelAnimationFrame(raf);
  }, [playing]);

  const [a, b] = glyphPaths(t);
  // A mouse click must not leave focus on the cover, or a later Space would keep it dimmed while playing.
  const click = (e: MouseEvent<HTMLButtonElement>) => { if (e.detail) e.currentTarget.blur(); onToggle(); };
  return (
    <button className={`cover-btn${playing ? "" : " paused"}`} aria-label={playing ? "Stop the record" : "Play the record"}
      style={{ left: cx - rl, top: cy - rl, width: 2 * rl, height: 2 * rl }} onClick={click}>
      <svg viewBox="8 8 20 20" fill="currentColor" aria-hidden><path d={a} /><path d={b} /></svg>
    </button>
  );
}
