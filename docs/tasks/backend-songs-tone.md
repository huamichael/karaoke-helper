# Task D: Songs and tone

**Owner:** to be assigned. **Works alongside:** B (API and Whisper base), C (CTC and rhythm).

## Goal

You own everything about Mandarin text and pitch. First you write the one function that turns Hanzi into syllable records, which both the song pipeline and the grader use. Then you build the pipeline that produces each song's bundle, and prepare the demo songs. Finally you build the tone scorer for Word practice.

## Status

As of 3 October 2026, every deliverable below is built and tested, except:

- Tuning `score_tones` on real recordings. Its constants come from synthetic voices. On our own spoken line takes it is still near chance, so tone stays off for lines.
- The fixture recordings in `backend/tests/fixtures/audio/`, which the team records.

Tone feedback is a tone tip in the syllable's hint (`TONE_TIPS` in `scoring/feedback.py`), shown in Word practice; the `TONE_<expected>_<heard>` code still records the tone the grader heard. Feedback never describes the attempt (scoring.md, Feedback).

The three demo songs are built: 月亮代表我的心, 一剪梅 and 茉莉花. Their `lyrics.yaml` files hold reading fixes, word fixes, translations and glosses.

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

You also add `pypinyin`, `jieba`, `praat-parselmouth` and `edge-tts` to `backend/pyproject.toml`, and the tone tips (`TONE_TIPS`) to `scoring/feedback.py`.

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

- Uses `jieba.cut` with `HMM=False`. For 我想和你一起 it returns 我 / 想 / 和 / 你 / 一起.
- jieba's dictionary is Simplified, and on Traditional text it splits badly (你問 / 我 / 愛). So each run of Hanzi is converted to Simplified with `zhconv`, segmented, and mapped back onto the original characters.
- jieba still makes mistakes (白人 for 白 / 人人). Fix them per song in the `words` block of `lyrics.yaml`.

### `build_song`

- Command line: `uv run python -m pipeline.build_song --id <song_id>`, or `--all` for every song. It reads `data/songs/<song_id>/lyrics.yaml` and writes `song.json` beside it, then prints a review table of every line's pinyin and words.
- `--no-clips` skips generating spoken clips, so no internet is needed. `--check` also cuts each line from the track into `check/<line>.wav`, so you can listen to whether the line times are right.
- Re-running keeps the syllable times `align_track` wrote, for every line whose text, start and readings did not change. Trimming a line's `end_ms` keeps its times; a syllable that now starts after the new end loses its time.

### Line timing: starting with the singing, and trimming long lines

Lyric timestamps are often 0.1–0.4 s late, so a line clips its first word and plays the start of the next line. Once `align_track` has run, `uv run --group vocals python -m pipeline.line_ends --song <id> --apply` corrects them and rebuilds `song.json`, editing only the `start_ms` and `end_ms` values in `lyrics.yaml`:

- Between two sung lines, the boundary moves to the quietest moment of the singer's voice (the separated `check/vocals.wav`) between the first line's last syllable and the second's first: the breath.
- After an instrumental break, a line starts 100 ms before the voice comes in: where it rises to within 10 dB of the line's peak (instruments leaking into the voice track stay 17–20 dB below), searched near the first aligned syllable.
- Without the voice track it falls back to 150 ms before the first aligned syllable; the aligner can run 0.1–0.3 s late and miss syllables, so this is rougher.
- Running it again changes nothing.

All three demo songs were corrected this way on 4 October 2026. Every cut between sung lines sits at least 25 dB below the singing, except 月亮代表我的心 line 7→8, where the singer glides into the next line without a breath (14 dB).


A line whose `end_ms` runs into the instrumental makes Listen play the extra music, and lengthens the recording limit. To trim:

1. Measure: `uv run --group vocals python -m pipeline.line_ends --song <id>`. Demucs separates the singer's voice once (cached in the git-ignored `check/vocals.wav`); for each line the tool prints the current `end_ms`, where the voice falls silent, and a suggested `end_ms`. It changes nothing.
2. Check by ear: `build_song --check` cuts each line to `check/<line>.wav`. Quiet endings, breaths and reverb can fool the measurement.
3. Edit that line's `end_ms` in `lyrics.yaml` (find it by `start_ms`), then rebuild with `build_song --id <id>`. Syllable times are kept. Or let `line_ends --apply --trim-fades --silence-db <n>` do it for every flagged line.
4. Leave a short margin (the tool adds 300 ms) so the last sound is not clipped. The next entry may start later than the new end; a gap between lines is fine.
- The `lyrics.yaml` format is in [data-model.md](../contracts/data-model.md), section 5. Every line carries `start_ms` and `end_ms`; lines with empty `text` mark instrumental gaps and are skipped.
- Reading fixes go in the song's `readings` block, keyed by phrase: `掩没: yan3 mo4`. `reading_overrides` (done) turns them into per-line positions for `to_syllables`. Songs often sing 的 as "dì" and 了 as "liǎo".
- For each line: `to_syllables` with that line's overrides, then `segment_words` to fill `word_index` and each word's `syllable_indices`.
- Word clips come from `edge-tts` with the `zh-CN-XiaoxiaoNeural` voice, saved as `words/<reading>.mp3` (for example `yue4-liang4.mp3`) so repeated words and homophones share one clip. Existing clips are reused.
- edge-tts reads the Hanzi itself and does not know about `readings` fixes. Listen to the clips of fixed words (`yan3-mo4.mp3`, `chang2-liu2.mp3`) to check it says them correctly.
- `translation` and `gloss` come from the song's `translations` and `glosses` blocks, or are `null`.
- Validate the output by loading it into the `Song` model before writing. Print a table of Hanzi and pinyin for the human review.
- The tracks are copyrighted and the repository is public, so `audio.mp3` is ignored by git and shared through the team folder. `lyrics.yaml` and `song.json` are committed.

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
- People move their pitch by different amounts, so each template may stretch between 0.5 and 2 times before comparing. Without this, a speaker with a shallow dip was heard as a level first tone.
- For a longer word, read each syllable from its span start to the next span's start, because CTC spans cover only part of a syllable. The last syllable runs to the last voiced frame, for at most `LAST_SYLLABLE_MAX_MS`. Then remove `SHAPE_WEIGHT` (0.75) of each syllable's mean from it and from the shapes, so shape counts most and height relative to the recording still counts a little. Removing nothing (the earlier rule) recognised 22% of syllables in two-syllable edge-tts word clips; these two changes recognise 59%.
- `heard` is the nearest template. The score falls as the distance to the expected template grows. Choose the scale so a clearly correct recording scores 85 or more.
- The expected tone comes from `sandhi_tones`, not from the syllable's lexical tone.

### `sandhi_tones`

- Applies the 一 and 不 rules, then third-tone sandhi, as listed in [scoring.md](../contracts/scoring.md), tone section. The team chose to include 一 and 不, so a learner who says 一片 as yí piàn is not marked wrong.
- It works from the syllables' Hanzi and lexical tones, not from pypinyin, because pypinyin already applies some 一 changes inside common words.
- Return `None` for the neutral tone.

### Fixtures

- `lines/<name>.json` is one `Line` object.
- `audio/<name>__<variant>__<speaker>.wav` and `tone/<reading>__<variant>__<speaker>.wav` are 16 kHz mono. Naming rules: backend-interfaces.md section 6.
- [docs/recording-session.md](../recording-session.md) is the guide for the people recording. `session.py` lists every recording; `prompts.py` makes a clip to copy for each; `check_recordings.py` checks the files.
- Three fixture lines exist, one per demo song: `yueliang`, `yijianmei`, `jasmine`. `backend/tests/fixtures/README.md` lists them and how to record each variant.

## Out of scope

- Whisper, the matcher and the API.
- Alignment and rhythm. C fills syllable times in `song.json`.
- Tone in sung lines. The melody replaces it, so it is never scored there.
- Melody.
