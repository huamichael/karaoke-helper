import { describe, expect, it } from "vitest";
import type { Line } from "../api/client";
import { phraseBreaks } from "./phrases";

/** A line whose words are given as Hanzi strings; text may contain spaces and punctuation. */
function line(text: string, words: string[]): Line {
  let s = 0;
  const syllables: Line["syllables"] = [];
  const ws = words.map((w, index) => {
    const idx = [...w].map((hanzi) => {
      syllables.push({ index: s, word_index: index, hanzi, pinyin: "", pinyin_numeric: "", initial: "", final: "", tone: 1, start_ms: null, end_ms: null });
      return s++;
    });
    return { index, text: w, syllable_indices: idx, gloss: null, audio_url: null };
  });
  return { index: 0, start_ms: 0, end_ms: 1000, text, translation: null, syllables, words: ws };
}

describe("phraseBreaks", () => {
  const long = line("讓我來將你摘下 送給別人家", ["讓", "我", "來", "將", "你", "摘下", "送給", "別人家"]);

  it("breaks a long line where its lyric has a space", () => {
    expect(phraseBreaks(long)).toEqual([5]);
  });
  it("treats Chinese punctuation as a phrase end too", () => {
    expect(phraseBreaks(line("两只老虎，两只老虎，跑得快", ["两只", "老虎", "两只", "老虎", "跑得快"]), 0)).toEqual([1, 3]);
  });
  it("leaves a short line on one row", () => {
    expect(phraseBreaks(line("好一朵 美丽", ["好", "一朵", "美丽"]))).toEqual([]);
  });
  it("never breaks after the last word", () => {
    expect(phraseBreaks(line("一二三四五六七八九十 ", ["一二", "三四", "五六", "七八", "九十"]), 0)).toEqual([]);
  });
});
