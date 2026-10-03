/**
 * Where a long line splits over two rows: at the phrase ends its lyric text
 * already marks with a space or punctuation ("讓我來將你摘下 送給別人家"), so a
 * line never wraps in the middle of a phrase.
 *
 * Owner: A. Spec: docs/design/ui.md §3.2 (the active line at 60px in a 760px column).
 */
import type { Line } from "../api/client";

/** About this many syllables fill the 760px column at the active line's size. */
export const LONG_LINE = 10;

const SEPARATOR = /[\s，。、！？；：,.!?;:]/;

/** Word indices after which a new row starts. Empty for a line short enough for one row. */
export function phraseBreaks(line: Line, minSyllables = LONG_LINE): number[] {
  const ss = line.syllables;
  if (ss.length < minSyllables) return [];
  const out: number[] = [];
  let k = 0;
  for (const ch of line.text) {
    if (k < ss.length && ch === ss[k].hanzi) {
      k++;
      continue;
    }
    if (!SEPARATOR.test(ch) || k === 0 || k >= ss.length) continue;
    const w = ss[k - 1].word_index;
    const word = line.words[w];
    const endsWord = word && word.syllable_indices[word.syllable_indices.length - 1] === k - 1;
    if (endsWord && w < line.words.length - 1 && !out.includes(w)) out.push(w);
  }
  return out;
}
