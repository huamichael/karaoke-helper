# Task D: Songs and tone

**Owner:** to be assigned. **Works alongside:** B (API and Whisper base), C (CTC and rhythm).

## Goal

You own everything about Mandarin text and pitch. First you write the one function that turns Hanzi into syllable records, which both the song pipeline and the grader use. Then you build the pipeline that produces each song's bundle, and prepare the demo songs. Finally you build the tone scorer for Word practice.

## Read first

1. [PROJECT_PLAN.md](../PROJECT_PLAN.md), sections 1, 2 and 4.
2. [contracts/data-model.md](../contracts/data-model.md): the syllable record, its conventions, and the song bundle. You implement most of this file.
3. [contracts/backend-interfaces.md](../contracts/backend-interfaces.md): `to_syllables`, `segment_words`, `sandhi_tones`, `score_tones`.
4. [contracts/scoring.md](../contracts/scoring.md): the tone section.

## What you own

```text
backend/app/mandarin.py           # to_syllables, segment_words, sandhi_tones
backend/pipeline/build_song.py    # lyrics + audio -> song.json and word clips
backend/app/scoring/pitch.py      # pitch contour helper
backend/app/scoring/tone.py       # score_tones
data/songs/<song_id>/             # the demo song bundles
backend/tests/fixtures/           # you keep it; everyone adds recordings
backend/tests/test_mandarin.py, test_tone.py
```

You also add `pypinyin`, `jieba`, `praat-parselmouth` and `edge-tts` to `backend/pyproject.toml`, and the `TONE_<expected>_<heard>` rows to `scoring/feedback.py`.

## What you use from others

| Thing | Owner | Until it exists |
|---|---|---|
| `schemas.py` types | B | Available at hour 1.5 |
| Syllable spans inside multi-syllable words | C, through the grader | Due at hour 13. Build and test tone on single-syllable words first; they need no spans. |
| Syllable times in `song.json` | C's `align_track` | Leave `start_ms` and `end_ms` as `None`. C fills them. |

## Deliverables

### By hour 2: text to syllables

B's matcher is blocked until this exists, so it comes first.

1. `to_syllables`.
2. `segment_words`.
3. `test_mandarin.py`, using the examples table in data-model.md section 2 as test cases.

**Done when:** every row of that table passes, and `to_syllables("我love你，好!")` returns three syllables.

### Block 1, hours 1.5–6: the pipeline and song 1

1. `build_song`.
2. `data/songs/<id>/` for song 1, with every reading checked by someone who reads Mandarin.
3. A spoken clip for every word.
4. The fixture lines in `backend/tests/fixtures/lines/`.

**Done when (checkpoint A):** B's real grader loads your `song.json` and grades a line from it.

### Block 2, hours 6–13: tone on single syllables

1. `pitch.py`.
2. `sandhi_tones`.
3. `score_tones` for one-syllable words, with `spans=None`.
4. Song 2.

**Done when:** on your own recordings of single-syllable words, the four tones said correctly are mostly recognised as themselves. Record the confusion you see and tell the team.

### Block 3, hours 13–19: tone on longer words

1. `score_tones` using the spans C provides.
2. Tone feedback rows.
3. Pinyin review of song 2.

**Done when:** with `ENABLE_TONE=1`, Word practice on a two-syllable word returns a tone result for each syllable.

## Implementation notes

### `to_syllables`

- Use pypinyin's `lazy_pinyin` with `strict=True` for initials and finals, `Style.TONE` for `pinyin`, and `Style.TONE3` with `neutral_tone_with_five=True` for `pinyin_numeric`.
- Pass `errors="ignore"` so non-Hanzi characters produce nothing. Keep only Hanzi in `hanzi` too, so the lists stay the same length.
- Run pypinyin on the whole string, not character by character. It uses context for characters with several readings.
- Apply `overrides` after pypinyin. An override gives a `pinyin_numeric` such as `di4`; derive the other fields from it.
- This is the only place in the project that calls pypinyin.

### `segment_words`

- Use `jieba.cut`. For 我想和你一起 it returns 我 / 想 / 和 / 你 / 一起.
- Check that the pieces joined together equal the Hanzi of the input.

### `build_song`

- Command line: `uv run python -m pipeline.build_song --id <song_id> --lrc lyrics.lrc --audio track.mp3 --title "..." --artist "..."`.
- Input lyrics are in LRC format, one `[mm:ss.xx] text` per line. Get them from LRCLIB or time them by hand.
- A line's `end_ms` is the next line's `start_ms`. Cap it so a line never runs through an instrumental break, and adjust by hand where needed.
- For each line: `to_syllables` with that line's overrides, then `segment_words` to fill `word_index` and each word's `syllable_indices`.
- `overrides.json` holds corrected readings, keyed by line index and character position. Songs often sing 的 as "dì" and 了 as "liǎo".
- Generate each word's clip with `edge-tts`, using a Mandarin voice such as `zh-CN-XiaoxiaoNeural`. Save it as `words/<line_index>_<word_index>.mp3` and set the word's `audio_url`.
- `translation` and `gloss` are filled by hand or left `null`.
- Validate the output by loading it into the `Song` model before writing. Print a table of Hanzi and pinyin for the human review.
- If the repository is public, do not commit copyrighted audio.

### Pitch

- Use `praat-parselmouth`: `Sound(samples, sampling_frequency=16000).to_pitch(time_step=0.01, pitch_floor=75, pitch_ceiling=500)`.
- Convert hertz to semitones and subtract the median of the whole recording.
- Unvoiced frames have no pitch. Drop them.
- If a syllable has under 50 ms of voiced frames, return `heard=None` and `score=None`.

### `score_tones`

- For each syllable, take the pitch frames inside its span. Drop the first and last tenth, which are distorted by the neighbouring sounds. Resample to five points.
- The standard tone shapes on the five-level scale are: tone 1 is 55 (high and level), tone 2 is 35 (rising), tone 3 is 214 (dipping), tone 4 is 51 (falling). A third tone that is not the last syllable of the word is usually just low and falling, 21.
- Turn those levels into semitones. One level is roughly 2 to 3 semitones; the exact figure depends on the speaker and needs tuning.
- For a one-syllable word there is nothing to compare the height against, so compare shape only: remove the mean from both the contour and the templates.
- For a longer word, remove the word's median instead, so the relative height of the syllables is kept.
- `heard` is the nearest template. The score falls as the distance to the expected template grows. Choose the scale so a clearly correct recording scores 85 or more.
- The expected tone comes from `sandhi_tones`, not from the syllable's lexical tone.

### `sandhi_tones`

- When two third tones are adjacent, the first is expected as a second tone. pypinyin can do this: `lazy_pinyin(text, style=Style.TONE3, tone_sandhi=True)` turns 你好 into `ni2 hao3`.
- Return `None` for the neutral tone.

### Fixtures

- `lines/<name>.json` is one `Line` object.
- `audio/<name>__<variant>.wav` is 16 kHz mono. The variants are listed in backend-interfaces.md section 6.
- At kickoff, collect everyone's recordings of the two hand-written lines.

## Out of scope

- Whisper, the matcher and the API.
- Alignment and rhythm. C fills syllable times in `song.json`.
- Tone in sung lines. The melody replaces it, so it is never scored there.
- Melody.
