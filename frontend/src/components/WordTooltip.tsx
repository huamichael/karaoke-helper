/**
 * Hovering a graded word shows, per syllable, the expected and heard initial and
 * final, and, once the CTC layer sends timing.offset_ms, how early or late it came
 * in. Everything is read from the result as sent.
 *
 * Owner: A. Spec: docs/design/ui.md §5.3.3 ("Hover a word", "Early or late").
 */
import type { AttemptResult, Part, SyllableResult, WordResult } from "../api/client";
import { notchPosition } from "../logic/timing";

function part(p: Part | null): string | null {
  if (!p) return null;
  if (p.heard == null) return `${p.expected || "–"} not heard`;
  return p.heard === p.expected ? p.expected : `${p.expected || "–"} → ${p.heard}`;
}

function timing(s: SyllableResult): string | null {
  const off = s.timing?.offset_ms;
  if (off == null) return null;
  return off === 0 ? "came in on time" : `came in ${Math.abs(off)} ms ${off < 0 ? "early" : "late"}`;
}

export function syllablesOf(result: AttemptResult, w: WordResult): SyllableResult[] {
  return w.syllable_indices.map((i) => result.syllables.find((s) => s.index === i)).filter((s): s is SyllableResult => !!s);
}

/** Where the bar's notch sits (logic/timing.ts), as CSS. Null without timing. */
export function notchOffset(ss: SyllableResult[]): string | null {
  const at = notchPosition(ss.map((s) => s.timing?.offset_ms));
  return at == null ? null : `${at}%`;
}

export function WordTooltip({ syllables }: { syllables: SyllableResult[] }) {
  if (!syllables.length) return null;
  return (
    <span className="wtip" role="tooltip">
      {syllables.map((s) => (
        <span className="wtip-row" key={s.index}>
          <b>{s.hanzi}</b>
          <span className="wtip-py">{s.pinyin}</span>
          {s.status === "missing" ? <span>not heard</span> : [part(s.initial), part(s.final)].filter(Boolean).map((t, k) => <span key={k}>{t}</span>)}
          {timing(s) && <span className="wtip-time">{timing(s)}</span>}
        </span>
      ))}
    </span>
  );
}
