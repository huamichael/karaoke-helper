# Contract: frontend ↔ backend API

**Keeper:** B. **Used by:** A (frontend), B (routes).

This is the only agreement the frontend depends on. The frontend can be built entirely against the mock grader, which returns valid results in this format from hour 1.

## Conventions

- JSON in snake_case.
- All times are integer milliseconds.
- All scores are integers from 0 to 100. A `null` score means "not evaluated", and the frontend hides it.
- The backend runs at `http://localhost:8000` in development.

## Endpoints

| Method and path | Returns | Notes |
|---|---|---|
| `GET /api/v1/songs` | `SongSummary[]` | |
| `GET /api/v1/songs/{id}` | `Song` | The contents of that song's `song.json` |
| `POST /api/v1/attempts` | `AttemptResult` | `multipart/form-data`; fields below |
| `GET /media/...` | audio file | Track and spoken word clips |
| `GET /api/v1/health` | `{ "status": "ok", "grader": string }` | `grader` is `mock` or `real` |

## Types

`Song`, `Line`, `Syllable` and `Word` are the song bundle defined in [data-model.md](data-model.md). They are repeated here in TypeScript because the frontend needs them in one place.

```ts
type SongSummary = { id: string; title: string; artist: string; line_count: number };

type Song = SongSummary & {
  audio_url: string;                  // full track; play [start_ms, end_ms] per line
  lines: Line[];
};

type Line = {
  index: number;
  start_ms: number; end_ms: number;   // position in audio_url
  text: string;                       // Hanzi
  translation: string | null;
  syllables: Syllable[];
  words: Word[];
};

type Syllable = {
  index: number;                      // position within the line
  hanzi: string;
  pinyin: string;                     // "xiǎng", for display
  pinyin_numeric: string;             // "xiang3"
  initial: string;                    // "" for syllables with no initial, such as 我 (wo)
  final: string;
  tone: 1 | 2 | 3 | 4 | 5;            // 5 = neutral
  word_index: number;
  start_ms: number | null;            // when the original singer sings it; null until the pipeline aligns the track
  end_ms: number | null;
};

type Word = {
  index: number;
  text: string;                       // "一起"
  syllable_indices: number[];
  gloss: string | null;               // English meaning
  audio_url: string | null;           // spoken reference; use browser speechSynthesis if null
};

// POST /api/v1/attempts form fields
//   audio       file    webm/opus from MediaRecorder (wav and mp4 also accepted), max 30 s
//   song_id     string
//   line_index  int
//   target      "line" | "word"     "line" = a sung line; "word" = Word practice
//   mode        "spoken" | "singing": required when target is "line"; ignored when target is "word"
//   word_index  int: required when target is "word"; omit when target is "line"

type Score = number | null;

type AttemptResult = {
  attempt_id: string;
  song_id: string; line_index: number; word_index: number | null;
  target: "line" | "word";
  mode: "spoken" | "singing" | null;  // null when target is "word"
  status: "ok" | "no_speech";         // no_speech: scores null, words [], syllables [], prompt a retry
  engine: string;                     // "mock" | "whisper" | "whisper+ctc": the layers that graded this attempt
  scores: {
    overall: Score; pronunciation: Score; completeness: Score;
    rhythm: Score;                    // singing-accuracy mode, from stage 3
    tone: Score;                      // Word practice, from stage 3
    melody: Score;                    // stretch goal; null
  };
  words: WordResult[];                // one per expected word, in order; the chips the user sees and clicks
  syllables: SyllableResult[];        // one per expected syllable, in order; the detail behind each word
  heard: { hanzi: string; pinyin: string } | null;   // what Whisper transcribed
  next_step:
    | { type: "practice_word"; word_index: number; message: string }
    | { type: "retry_line" | "next_line"; message: string };
};

type WordResult = {
  index: number; text: string; pinyin: string;
  status: "good" | "ok" | "wrong" | "missing";   // show as green / yellow / red / grey; pronunciation only, never rhythm
  score: Score;
  syllable_indices: number[];         // which entries of syllables[] belong to this word
  // rhythm: "early" | "late" | "on_time" | null;  // DISABLED: see "Rhythm marker (disabled)" below
};

type SyllableResult = {
  index: number; hanzi: string; pinyin: string;
  status: "good" | "ok" | "wrong" | "missing";
  score: Score;
  initial: Part | null;               // null for syllables with no initial, unless the user added one: then expected is ""
  final: Part | null;
  tone: { expected: number; heard: number | null; score: Score } | null;  // Word practice, from stage 3
  timing: {                           // null unless the CTC layer ran
    start_ms: number; end_ms: number; // where the syllable sits in the user's recording
    offset_ms: number | null;         // early (negative) or late (positive) against the original; null until stage 3
    score: Score;                     // this syllable's rhythm score; null until stage 3
  } | null;
  feedback: { code: string; message: string } | null;   // null when status is "good"
};

type Part = { expected: string; heard: string | null; score: Score };
```

## Errors

Any non-2xx response has the body `{ "error": { "code": string, "message": string } }`.

| HTTP status | `code` | When |
|---|---|---|
| 404 | `song_not_found`, `line_not_found`, `word_not_found` | An id or index does not exist |
| 413 | `audio_too_long` | The recording is longer than 30 seconds |
| 422 | `bad_audio` | The file cannot be decoded |
| 422 | `bad_request` | A required field is missing, or `mode` is absent when `target` is `line` |
| 500 | `grading_failed` | An unexpected failure while grading |

A recording with no detectable speech is not an error. It returns 200 with `status: "no_speech"`.

## Example result

The user chose spoken-accuracy mode, sang 我想和你一起, and pronounced 你 (nǐ) closer to "lǐ". Only the flagged word and its syllable are shown.

```jsonc
{
  "attempt_id": "att_0007",
  "song_id": "song_001",
  "line_index": 3,
  "word_index": null,
  "target": "line",
  "mode": "spoken",
  "status": "ok",
  "engine": "whisper",
  "scores": {
    "overall": 98, "pronunciation": 97, "completeness": 100,
    "rhythm": null, "tone": null, "melody": null
  },
  "words": [
    // ... 我, 想, 和 with status "good" ...
    { "index": 3, "text": "你", "pinyin": "nǐ", "status": "ok", "score": 83, "syllable_indices": [3] }
    // ... 一起 with status "good" ...
  ],
  "syllables": [
    // ... 我, 想, 和 with status "good" ...
    {
      "index": 3, "hanzi": "你", "pinyin": "nǐ",
      "status": "ok", "score": 83,
      "initial": { "expected": "n", "heard": "l", "score": 60 },
      "final":   { "expected": "i", "heard": "i", "score": 100 },
      "tone": null,
      "timing": null,
      "feedback": {
        "code": "INITIAL_N_L",
        "message": "Sounded closer to \"l\". For \"n\", keep the tongue tip behind your top teeth and let the air go through your nose."
      }
    }
    // ... 一, 起 with status "good" ...
  ],
  "heard": { "hanzi": "我想和李一起", "pinyin": "wǒ xiǎng hé lǐ yì qǐ" },
  "next_step": {
    "type": "practice_word", "word_index": 3,
    "message": "Say 你 (nǐ) on its own, then retry the line."
  }
}
```

The same attempt in singing-accuracy mode would report `"engine": "whisper+ctc"`, a `timing` object on every syllable and, from stage 3, a `rhythm` score.

## Rhythm marker (disabled)

Word colour shows pronunciation only, in both modes. A separate early/late marker under each word in singing mode is written but commented out. To enable it, uncomment all five parts in one commit:

1. `backend/app/schemas.py`: the `rhythm` field on `WordResult`.
2. `backend/app/scoring/grader.py`: the `_word_rhythm` function, and `rhythm=_word_rhythm(parts),` in `_word_result`.
3. `frontend/src/components/WordChips.tsx`: the marker under the word.
4. `frontend/src/styles/lyrics.css`: the `.word .rhythm` styles.
5. This file: the `rhythm` line in `WordResult` above.

Then regenerate `frontend/src/api/types.ts` (`scripts/gen-types.sh`) and add a grader test. A word's rhythm comes from its worst-timed syllable: `on_time` when that syllable's rhythm score is 85 or above, otherwise `early` or `late` by the sign of its offset. It is `null` in spoken mode and Word practice, where rhythm is not scored.

## Rules

- **Source of truth.** The Pydantic models in `backend/app/schemas.py` define this contract in code. TypeScript types are generated from the backend's OpenAPI output with `openapi-typescript`, never written by hand.
- **No scoring logic in the frontend.** The backend sends `status` and the feedback `message`. The frontend only renders them.
- **Show what is not null.** The frontend displays every score that is not `null`. New scores appear when their stage lands, with no frontend change.
- **Any word is clickable.** `next_step` suggests one word to practise, but the user can open Word practice on any word. The frontend sends `target=word` with that word's `word_index`.
- **Changes.** Adding a field is fine at any time. Renaming or removing one needs the frontend developer's agreement first. Edit this file in the same commit as the code.
