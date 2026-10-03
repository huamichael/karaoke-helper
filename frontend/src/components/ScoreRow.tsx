/**
 * The row of scores for an attempt.
 *
 * Shows every score that is not null and hides the rest, so Rhythm and Tone appear
 * by themselves when the backend starts sending them. Fresh scores count up.
 *
 * Owner: A. Spec: docs/tasks/frontend.md, docs/design/ui.md §3.3 ("Result reveal").
 */
import { useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";
import type { Scores } from "../api/client";

const NAMES: [keyof Scores, string][] = [
  ["overall", "Overall"], ["pronunciation", "Pronunciation"], ["completeness", "Completeness"],
  ["rhythm", "Rhythm"], ["tone", "Tone"], ["melody", "Melody"],
];

function CountUp({ value, animate }: { value: number; animate: boolean }) {
  const el = useRef<HTMLElement>(null);
  const reduced = useReducedMotion();
  useEffect(() => {
    const b = el.current;
    if (!b) return;
    if (!animate || reduced) { b.textContent = String(value); return; }
    const t0 = performance.now();
    let raf = requestAnimationFrame(function frame(now) {
      const p = Math.min(1, (now - t0) / 900);
      b.textContent = String(Math.round(value * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(frame);
    });
    return () => cancelAnimationFrame(raf);
  }, [value, animate, reduced]);
  return <b ref={el}>{animate && !reduced ? 0 : value}</b>;
}

export function ScoreRow({ scores, fresh = false }: { scores: Scores; fresh?: boolean }) {
  const shown = NAMES.filter(([k]) => scores[k] != null);
  if (!shown.length) return null;
  return (
    <div className="scores">
      {shown.map(([k, name]) => (
        <span key={k}>{name}<CountUp value={scores[k]!} animate={fresh} /></span>
      ))}
    </div>
  );
}
