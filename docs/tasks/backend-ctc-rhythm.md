# Task C: CTC layer and rhythm

**Owner:** to be assigned. **Works alongside:** B (API and Whisper base), D (songs and tone).

## Goal

You build the in-depth grading layer. A CTC acoustic model aligns the expected syllables to the audio. From that you provide three things: where each syllable starts and ends, a finer score for each sound, and a rhythm score. You also use the same alignment on the original song track, so the reference and the user's attempt are measured the same way.

This is the least proven part of the project. Your first block is an experiment, and checkpoint B decides how much of your layer reaches users.

## Read first

1. [PROJECT_PLAN.md](../PROJECT_PLAN.md), sections 1 to 4.
2. [contracts/data-model.md](../contracts/data-model.md): the syllable record you receive and the times you fill in.
3. [contracts/backend-interfaces.md](../contracts/backend-interfaces.md): `align`, `score_sounds`, `score_rhythm`, and the list rule.
4. [contracts/scoring.md](../contracts/scoring.md): the CTC layer and rhythm sections.

## What you own

```text
backend/app/scoring/ctc.py         # align, score_sounds
backend/app/scoring/rhythm.py      # score_rhythm
backend/pipeline/align_track.py    # fills syllable times in song.json
backend/tests/test_ctc.py, test_rhythm.py
backend/tests/eval_ctc.py          # the checkpoint B script
```

You also add `torch` and `torchaudio` to `backend/pyproject.toml`, and the `RHYTHM_EARLY` and `RHYTHM_LATE` rows to `scoring/feedback.py`.

## What you use from others

| Thing | Owner | Until it exists |
|---|---|---|
| `schemas.py` types | B | Available at hour 1.5 |
| `scoring/confusions.py` | B | Available in block 1; the pairs are listed in scoring.md |
| Fixture recordings and lines | everyone, kept by D | Recorded at kickoff |
| `song.json` for song 1 | D | Due at hour 6; use the fixture lines before that |

You never need Whisper, the API or the frontend to do your work. Every function you write takes an `Audio` and a `list[Syllable]`.

## Deliverables

### Block 1, hours 1.5–6: the experiment

Answer four questions and report them to the team:

1. **Does forced alignment run?** Check `torchaudio.functional.forced_align` in the version you pin. It was scheduled for removal and then kept. The fallback is the `ctc-forced-aligner` package.
   - Pin `torch` to the release that matches `torchaudio`. In October 2026 an unpinned lock resolved `torch` 2.14 with `torchaudio` 2.11, because torchaudio is in maintenance mode and releases less often. A compiled torchaudio built for a different torch version can fail to import. For example: `torch==2.11.*`, `torchaudio==2.11.*`.
   - `backend/pyproject.toml` already sends both packages to the CPU-only PyTorch index on Linux. Do not remove that.
2. **Which model?** Start with `torchaudio.pipelines.MMS_FA`. It aligns romanised text, so toneless pinyin goes in directly. `kehanlu/mandarin-wav2vec2-aishell1` is the alternative, but it outputs characters, which makes comparing sound variants harder.
3. **Are the boundaries right?** Align the fixture recordings, cut the audio at each span, and listen to the clips. Do this for sung lines and for spoken words.
4. **How fast is it?** Time one 5-second clip on the demo Mac.

**Done when:** the team knows the answers, and you can print a span for every syllable of a fixture line.

### Block 2, hours 6–13: the layer

1. `align`.
2. `score_sounds`.
3. `align_track`, run on song 1.
4. `eval_ctc.py`.

**Done when (checkpoint B):** `eval_ctc.py` runs over the fixture recordings and shows, for the Whisper base and for your layer, how many deliberate errors were flagged and how many correct syllables were wrongly flagged. The team picks one of the three outcomes in PROJECT_PLAN.md section 3.

### Block 3, hours 13–19: rhythm

1. `score_rhythm`.
2. Rhythm feedback rows.
3. `align_track` on song 2.
4. Tuning from the saved attempts.

**Done when:** in singing-accuracy mode with `ENABLE_RHYTHM=1`, a line sung in time scores clearly higher than the same line sung with two syllables rushed.

## Implementation notes

### Emissions

- Run the model once per recording to get a matrix of log-probabilities: one row per 20 ms frame, one column per token.
- `align` and `score_sounds` both need it. Cache it per `Audio` object so the second call does not run the model again.
- Load the model once and keep it in memory.

### Turning syllables into tokens

- The model was trained on standard pinyin spelling, so build each syllable's letters from `pinyin_numeric` without the tone digit: `jiu`, `hui`, `wo`. Do not join `initial` and `final`; those use the strict forms `iou`, `uei`, `uo`.
- ü appears as `v` in `pinyin_numeric`. The model may expect another spelling. Try `v`, `u` and `yu` on a recording of 女 or 绿 and keep whichever aligns best.
- Concatenate the letters of all syllables, align once, then split the frame path back into syllables by letter count.

### `align`

- `start_ms` and `end_ms` come from the first and last frame of the syllable's letters, times 20.
- `confidence` is the mean per-frame probability of the aligned tokens inside the span.
- Return `None` for a syllable whose span is shorter than 40 ms or whose confidence is very low. Start with 0.1 as the cut-off and tune it.

### `score_sounds`

- For each syllable, build its variants: the expected spelling, plus one for each confused partner of its initial and of its final (from `confusions.py`). For example `zhun` gives `zun`, and `san` gives `sang`.
- Score each variant on the frames around the syllable's span, with about 100 ms of margin on each side. The score is the mean log-probability along the best path.
- `heard` is the variant that scores highest. The component score depends on how far the expected spelling is ahead of, or behind, the best other variant.
- Suggested starting mapping: expected ahead by a clear margin gives 100; level gives about 70; a variant clearly ahead gives 40. Scoring.md requires 60 or below when a variant wins. Tune on the fixtures.
- A component with no confused partner falls back to the span's `confidence`.
- These numbers are starting points, not measurements.

### `score_rhythm`

- Take the reference syllables' `start_ms`, each measured from the first syllable of the line. Take the user's from `spans`.
- Fit a straight line from reference times to user times by least squares, over the syllables that are aligned on both sides. The slope absorbs tempo; the intercept absorbs the starting point.
- For each syllable, `offset_ms` is the signed distance from the line and `score = round(100 * exp(-abs(offset_ms) / 400))`.
- The line's score is the mean. Return `None` with fewer than three aligned syllables or when the reference has no times.

### `align_track`

- Command line: `uv run python -m pipeline.align_track --song <id> [--vocals path/to/vocals.wav]`.
- For each line, decode the track from 200 ms before `line.start_ms` to 200 ms after `line.end_ms`. Do not trim silence. Build an `Audio` with `trim_offset_ms=0`.
- Call the same `align` used on user recordings. Convert the spans to track time and write them into each syllable's `start_ms` and `end_ms`.
- Print each line's mean confidence, so badly aligned lines stand out.
- Instruments make alignment worse. `--vocals` lets you align against an isolated vocal file instead of the full mix. If a line is still wrong, correct the times by hand in `song.json`.

### `eval_ctc.py`

- For every fixture recording, print each syllable's Whisper-base score and CTC score side by side.
- The file name says what is wrong (`error-zh-z`, `missing-3`), so the script knows which syllable should be flagged.
- Summarise: errors caught and correct syllables wrongly flagged, for each layer.
- Write the audio cut at each span to a temporary folder, for listening.

## Out of scope

- Whisper, the matcher and the API.
- Tone. D scores it; you only supply the spans, through the grader.
- Melody.
