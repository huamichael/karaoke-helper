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
   - This implementation pins `torch==2.11.*` and `torchaudio==2.11.*` for reproducibility. TorchAudio 2.11 supports PyTorch 2.11 and later through its stable ABI; older releases require matching versions. Both 2.11 imports and a compiled CPU forced-alignment call have been checked on macOS.
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

- Timing uses the verified model stride. `start_ms` is the first token frame; `end_ms` is the exclusive boundary after the last token frame, clipped to the recording duration.
- `confidence` is the mean per-frame probability of the aligned tokens inside the span.
- Return `None` for a syllable whose span is shorter than 40 ms or whose confidence is very low. Start with 0.1 as the cut-off and tune it.

### `score_sounds`

- For each syllable, build its variants: the expected spelling, plus one for each confused partner of its initial and of its final (from `confusions.py`). For example `zhun` gives `zun`, and `san` gives `sang`.
- Score each variant on the frames around the syllable's span, with about 100 ms of margin on each side. The score is the mean log-probability along the best path.
- `heard` is the variant that scores highest. The component score depends on how far the expected spelling is ahead of, or behind, the best other variant.
- Compare initials and finals independently, keeping the other component fixed. The existing experimental mapping is kept in `ctc.py`; a winning alternative is capped at 60 as scoring.md requires, and ties prefer the expected sound. No parameters have been tuned without human recordings.
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
- Session filenames are `<line>__<variant>__<speaker>.wav`, with indexed errors such as `error-4-l-n` and `missing-4` (zero-based). Naming rules are in backend-interfaces.md section 6. Legacy unindexed error pairs require `--labels` when several syllables could be targeted. Unknown/ambiguous fixtures fail before models run.
- Summarise errors caught and correct syllables wrongly flagged for each layer. A missing syllable or any component score at most 60 counts as flagged, including a confused component in an otherwise `ok` syllable.
- Write the audio cut at each span to a temporary folder, for listening.

## Out of scope

- Whisper, the matcher and the API.
- Tone. D scores it; you only supply the spans, through the grader.
- Melody.


## Implemented status and running (3 October 2026)

Alignment, per-component likelihood scoring, the track CLI, and checkpoint evaluation are implemented. The grader calls rhythm behind the existing switch. Following main's Task B integration, poor rhythm lowers a syllable that is still `good` after sound and tone checks to the rhythm score's status; the syllable's numeric score remains its sound score. Early/late feedback follows sound and tone feedback in priority. All optional-layer switches still default to off. The syllable types and public scoring function signatures are unchanged.

The model is MMS_FA on CPU, with its wildcard output disabled because only known pinyin tokens are aligned. Its convolution stride is checked at load time. Emissions are cached by Audio identity with weak references and an eight-recording bound. Treat samples as immutable during a grading attempt. Imports and weight loading are lazy. The first model download is about 1.18 GB; subsequent runs use the PyTorch cache (`TORCH_HOME` may override it).

From `backend/`:

```bash
uv sync
uv run pytest
uv run python -m pipeline.align_track --song yue-liang-dai-biao-wo-de-xin
uv run python -m pipeline.align_track --song yi-jian-mei
uv run python tests/eval_ctc.py --output /path/to/clips --report /path/to/checkpoint.json
```

`align_track` also accepts `--dry-run` and `--vocals /path/to/vocals.wav`. Vocal audio must have the same time origin as the full track. The track is decoded once with PyAV and each line is sliced with context without trimming silence. Only syllable timings change; a failed run or a concurrent bundle edit leaves the original JSON intact. Rerunning replaces existing syllable timings, so preserve hand corrections before rerunning.

Evaluation uses the shared session filename parser for `<line>__<variant>__<speaker>.wav`, including `yijianmei__error-2-ing-in__mei.wav`. Indexed errors must match the expected confused sound at that index; annotations cannot override an indexed error or omission. Older two-field names still work, with `--labels` available for ambiguous unindexed errors, for example `{"yijianmei__error-n-l.wav": [5]}`.

Every recording's name, labels and 16 kHz mono PCM16 WAV data are checked before either model runs. Stale label filenames, contradictory indices, unsupported variants and truncated WAVs fail explicitly. `no_speech` follows the production grader's gate: both layers count the expected syllables as missing and CTC is skipped. These rejected recordings remain visible in the report.

Evaluation exports listening clips to a persistent temporary folder or `--output /path/to/clips`. Counts are printed both across all recordings and per speaker. Optional `--report /path/to/checkpoint.json` saves the counts, deliberate-error indices, transcript, component scores, flags and spans. Report spans use trimmed sample time; add the recording's `trim_offset_ms` to locate them in the original recording. A JSON report records a pending team decision, not a passed checkpoint. No recordings means a nonzero exit and an explicit pending-checkpoint message, never a passing report. To inspect performance or umlaut spelling independently:

```bash
uv run python tests/eval_ctc.py --benchmark /path/to/five-seconds.wav --line tests/fixtures/lines/yueliang.json --runs 3
uv run python tests/eval_ctc.py --umlaut /path/to/nv.wav --line /path/to/nv-line.json
```

The umlaut probe compares `v`, `u`, and `yu`, reusing emissions and exporting each spelling's spans. Until human recordings establish otherwise, standard `v` remains the default. The benchmark uses fresh Audio objects for warmed repetitions, so it measures inference rather than cache hits. Its cold measurement includes model loading and a download if necessary.

### Evidence and outstanding review

- Current checkout is based on main `12ba760` (including Task B's scoring integration and matching contract update). The alignment contract's standard-pinyin sentence was corrected with the developer's explicit approval; main's scoring contract remains unchanged.
- Current backend regression suite: 621 passed, 15 skipped, run with `.venv/bin/python -m pytest -q` from `backend/`. `git diff --check` passes. The skipped tests are existing stub/optional checks, not human CTC accuracy evidence. The earlier implementation passed `uv lock --check --offline`; uv is unavailable on the current shell path, so that check was not repeated in this iteration.
- Native macOS: pinned packages import; compiled forced alignment runs; MMS_FA loaded and ran on both sung full-mix audio and a generated spoken 月亮 reference. Speech synthesis is a smoke test, not human accuracy evidence.
- A five-second sung reference measured 2.646 s cold with weights already downloaded, and a 0.270 s warmed mean over three alignment-plus-scoring runs. This is a local Mac measurement, not a guarantee for other machines.
- Generated provisional timings: 月亮代表我的心 has 182/193 usable syllable spans (11 missing); 一剪梅 has 142/146 (4 missing). Missing times remain null. Moon-song lines 3, 14, 16, 22, 24 and Yi Jian Mei lines 1, 18 require particular review. Neither bundle's times have been approved by human listening.
- Original full-mix singing and even the spoken synthetic reference produced some low confidence/false-looking sound grades. Do not treat these exploratory scores as calibrated pronunciation measurements.
- The human fixture audio directory is empty. Deliberate-error detection, false-flag rates, rushed human singing, and the final checkpoint B decision remain pending the team's recordings and listening review.
- Docker/WSL runtime verification is pending: the local Docker daemon is stopped. The lockfile retains CPU-only Linux builds and no CUDA dependencies; native and container entry points use the same code and lock.

The deterministic tests cover spelling, repeated tokens, span confidence/duration, emission reuse/release, component alternatives, Viterbi likelihood against exhaustive CTC paths, pipeline writes, session and legacy evaluation filenames, label contradictions, WAV preflight, no-speech gating, per-speaker JSON counts, and rhythm integration/fallback. Complete the human checkpoint before enabling `ENABLE_CTC=1` and `ENABLE_RHYTHM=1` for the demo.
