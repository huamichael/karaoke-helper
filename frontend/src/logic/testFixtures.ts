/**
 * Test data shaped like the API (contracts/api.md): one line of 两只老虎 and
 * attempt results for it. Used only by the unit tests.
 *
 * Owner: A.
 */
import type { AttemptResult, Line, NextStep, Status } from "../api/client";

const syl = (index: number, word_index: number, hanzi: string, pinyin: string, initial: string, final: string) => ({
  index, word_index, hanzi, pinyin, pinyin_numeric: pinyin, initial, final, tone: 3, start_ms: null, end_ms: null,
});

export const LINE: Line = {
  index: 0,
  start_ms: 0,
  end_ms: 4000,
  text: "两只老虎，两只老虎",
  translation: "Two tigers, two tigers",
  syllables: [
    syl(0, 0, "两", "liǎng", "l", "iang"), syl(1, 0, "只", "zhī", "zh", "i"),
    syl(2, 1, "老", "lǎo", "l", "ao"), syl(3, 1, "虎", "hǔ", "h", "u"),
    syl(4, 2, "两", "liǎng", "l", "iang"), syl(5, 2, "只", "zhī", "zh", "i"),
    syl(6, 3, "老", "lǎo", "l", "ao"), syl(7, 3, "虎", "hǔ", "h", "u"),
  ],
  words: [
    { index: 0, text: "两只", syllable_indices: [0, 1], gloss: "two (of an animal)", audio_url: null },
    { index: 1, text: "老虎", syllable_indices: [2, 3], gloss: "tiger", audio_url: null },
    { index: 2, text: "两只", syllable_indices: [4, 5], gloss: "two (of an animal)", audio_url: null },
    { index: 3, text: "老虎", syllable_indices: [6, 7], gloss: "tiger", audio_url: null },
  ],
};

let n = 0;

export function lineResult(statuses: Status[], next: NextStep = { type: "next_line", message: "On to the next line." }, lineIndex = 0): AttemptResult {
  return {
    attempt_id: `att_${++n}`, song_id: "demo", line_index: lineIndex, word_index: null,
    target: "line", mode: "spoken", status: "ok", engine: "mock",
    scores: { overall: 90, pronunciation: 90, completeness: 100, rhythm: null, tone: null, melody: null },
    words: statuses.map((status, index) => ({ index, text: "两只", pinyin: "liǎng zhī", status, score: 90, syllable_indices: [2 * index, 2 * index + 1] })),
    syllables: [],
    heard: { hanzi: "两只老虎", pinyin: "liǎng zhī lǎo hǔ" },
    next_step: next,
  };
}

export function wordResult(status: Status, wordIndex = 1, lineIndex = 0): AttemptResult {
  return {
    attempt_id: `att_${++n}`, song_id: "demo", line_index: lineIndex, word_index: wordIndex,
    target: "word", mode: null, status: "ok", engine: "mock",
    scores: { overall: 80, pronunciation: 80, completeness: 100, rhythm: null, tone: null, melody: null },
    words: [{ index: wordIndex, text: "老虎", pinyin: "lǎo hǔ", status, score: 80, syllable_indices: [0, 1] }],
    syllables: [],
    heard: null,
    next_step: { type: "retry_line", message: "Now retry the line." },
  };
}

export function noSpeech(target: "line" | "word" = "line", lineIndex = 0): AttemptResult {
  return {
    attempt_id: `att_${++n}`, song_id: "demo", line_index: lineIndex, word_index: target === "word" ? 1 : null,
    target, mode: target === "line" ? "spoken" : null, status: "no_speech", engine: "mock",
    scores: { overall: null, pronunciation: null, completeness: null, rhythm: null, tone: null, melody: null },
    words: [], syllables: [], heard: null,
    next_step: { type: "retry_line", message: "We didn't hear anything. Try again." },
  };
}

export const blob = () => new Blob(["x".repeat(4096)], { type: "audio/webm" });
