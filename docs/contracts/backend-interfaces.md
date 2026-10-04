# Contract: backend interfaces

**Keeper:** B. **Used by:** B, C, D.

The backend is built as three independent tasks. This file is the agreement between them: who owns which module, the exact functions each one provides, and how the pieces are integrated. Read [data-model.md](data-model.md) first; every function here passes syllable records around.

## 1. Ownership

Each file has one owner. Nobody edits another owner's file without asking.

| Module | Owner | Provides |
|---|---|---|
| `backend/app/schemas.py` | B keeps it; all three agree changes | Every shared type |
| `backend/app/main.py`, `config.py`, `songs.py` | B | Routes, layer switches, song loading |
| `backend/app/audio.py` | B | `load_audio` |
| `backend/app/attempts.py` | B | Saves each real-graded attempt to `data/attempts/` |
| `backend/app/scoring/transcribe.py` | B | `transcribe` |
| `backend/app/scoring/matcher.py` | B | `match`, `score_sounds_base` |
| `backend/app/scoring/grader.py`, `mock.py` | B | `grade`, the mock grader |
| `backend/app/scoring/confusions.py` | B | The confused-pairs table |
| `backend/app/scoring/feedback.py` | B; C and D add rows for their codes | Feedback messages |
| `backend/app/scoring/ctc.py` | C | `align`, `score_sounds` |
| `backend/app/scoring/rhythm.py` | C | `score_rhythm` |
| `backend/pipeline/align_track.py` | C | Fills syllable times in `song.json` |
| `backend/app/mandarin.py` | D | `to_syllables`, `segment_words`, `sandhi_tones` |
| `backend/app/scoring/pitch.py`, `tone.py` | D | `score_tones` |
| `backend/pipeline/build_song.py` | D | Builds `song.json` and word clips |
| `backend/pipeline/line_ends.py`, `separate.py`, `instrumental.py` | D | Line times from the singer's voice; Demucs separation; Karaoke mode's `instrumental.mp3` |
| `backend/pipeline/whisper_words.py` | B | Isolated-word Whisper experiment |
| `data/songs/` | D | The demo song bundles |
| `backend/tests/fixtures/` | D keeps it; everyone adds recordings | Shared test data |
| `compose.yaml`, `docker/` | B | The Docker dev environment |

## 2. Shared types

All of these live in `backend/app/schemas.py`. `Syllable`, `LyricSyllable`, `Word`, `Line` and `Song` are defined in [data-model.md](data-model.md). The API result types are defined in [api.md](api.md).

```python
@dataclass
class Audio:
    samples: np.ndarray        # float32, mono, values in [-1, 1]
    sample_rate: int           # always 16000
    trim_offset_ms: int        # how much was cut from the start when silence was trimmed

class Transcript(BaseModel):
    text: str                  # Hanzi from Whisper, non-Hanzi characters removed
    syllables: list[Syllable]  # to_syllables(text), with tone set to None and no times
    no_speech: bool            # True when nothing usable was heard

class Span(BaseModel):
    start_ms: int              # measured within Audio.samples
    end_ms: int
    confidence: float          # 0-1: how well the expected sounds fit inside the span

class Part(BaseModel):         # the same shape the API returns
    expected: str
    heard: str | None
    score: int | None

class SoundScore(BaseModel):
    initial: Part | None       # None when the syllable has no initial and none was heard
    final: Part

class ToneGrade(BaseModel):
    expected: int              # after sandhi
    heard: int | None          # None when no clear pitch was found
    score: int | None

class RhythmSyllable(BaseModel):
    offset_ms: int             # negative = early, positive = late
    score: int

class RhythmResult(BaseModel):
    score: int                 # the line's rhythm score
    syllables: list[RhythmSyllable | None]
```

## 3. Functions

### The list rule

Every function that returns a per-syllable list returns **exactly one entry per expected syllable, in the same order**. `None` means "nothing for this syllable". The grader merges layers by index and never has to re-align anything.

### Provided by B

```python
def load_audio(data: bytes) -> Audio
```
- Decodes webm/opus, mp4 or wav. Resamples to 16 kHz mono. Trims leading and trailing silence, keeping a 150 ms margin.
- Raises `BadAudio` if the bytes cannot be decoded, and `AudioTooLong` (a subclass of `BadAudio`) if the recording is longer than 30 seconds.

```python
def transcribe(audio: Audio) -> Transcript
```
- Runs Whisper with the language fixed to Chinese and no prompt.
- Engine: `mlx-whisper` on macOS, `faster-whisper` elsewhere. Override with `WHISPER_ENGINE=mlx` or `faster`. `mlx` is rejected off macOS. `faster-whisper` uses `beam_size=5` and honours `WHISPER_VAD`. `mlx-whisper` 0.4.3 has no beam search, so it decodes greedily at temperature 0; `WHISPER_VAD` does not apply.
- Sets `no_speech=True` when Whisper returns nothing or only non-Hanzi text. Latin-letter tokens are suppressed during decoding, so English words for Mandarin speech ("How" for hào) do not end up as no speech.

```python
def match(expected: list[Syllable], heard: list[Syllable]) -> list[Syllable | None]
```
- Lines up a free transcript against the expected syllables. Returns the observed syllable for each expected one, or `None` if missing. Extra heard syllables are discarded.

```python
def score_sounds_base(expected: list[Syllable], observed: list[Syllable | None]) -> list[SoundScore | None]
```
- The Whisper-base component scores: 100, 60, 20, or `None` for a missing syllable. Rules in [scoring.md](scoring.md).

```python
def grade(audio: Audio, line: Line, target: str, mode: str | None, word_index: int | None) -> AttemptResult
```
- The orchestrator (section 4). The only function the routes call.

### Provided by C

```python
def align(audio: Audio, expected: list[Syllable]) -> list[Span | None]
```
- Forced-aligns the expected syllables to the audio. `None` for a syllable that has no usable span.
- Uses standard spelling from `pinyin_numeric` with the tone digit removed for alignment. Uses strict `initial` and `final` fields to construct confused-sound variants and label component scores. Ignores tone.
- Must work on a user recording and on a segment of the original song track. `align_track` calls it for the second case.

```python
def score_sounds(audio: Audio, expected: list[Syllable], spans: list[Span | None]) -> list[SoundScore | None]
```
- The CTC component scores, same return type as `score_sounds_base`. `None` marks the syllable as missing.

```python
def score_rhythm(reference: list[Syllable], spans: list[Span | None]) -> RhythmResult | None
```
- `reference` carries the original singer's `start_ms`. `spans` are the user's.
- Returns `None` when the reference has no times or fewer than three syllables are aligned.

### Provided by D

```python
def to_syllables(text: str, overrides: dict[int, str] | None = None) -> list[Syllable]
```
- The only place Hanzi becomes syllable records. One syllable per Hanzi character; other characters are dropped.
- `overrides` maps a character position in `text` to a `pinyin_numeric` reading, for example `{5: "di4"}`. Every character counts toward the position, spaces and punctuation included.
- Raises `ValueError` if an override does not point at a Hanzi character, if it is not a valid reading, or if a character has no known reading. pypinyin covers all CJK characters, so the last case should not occur with Whisper output.
- Returns the lexical `tone`. Times are `None`.
- Works for both Simplified and Traditional characters.

```python
def segment_words(text: str) -> list[str]
```
- Splits a line into words. The words joined together equal the Hanzi of `text`.

```python
def sandhi_tones(syllables: list[Syllable]) -> list[int | None]
```
- The tone each syllable is expected to be spoken with, after tone sandhi: the 一 and 不 rules, then third-tone sandhi (rules in [scoring.md](scoring.md), tone section). `None` for the neutral tone, which is not scored.

```python
def score_tones(audio: Audio, expected: list[Syllable], spans: list[Span | None] | None) -> list[ToneGrade | None]
```
- `spans=None` is allowed only when `expected` has one syllable. The whole voiced part of the recording is used.
- `None` for a syllable whose tone is not scored.

## 4. How the grader combines them

```python
def grade(audio, line, target, mode, word_index):
    expected = line.syllables if target == "line" else syllables_of(line, word_index)
    layers = config.layers_for(target, mode, syllable_count=len(expected))

    transcript = transcribe(audio)                           # B
    if transcript.no_speech:
        return no_speech_result(...)

    observed = match(expected, transcript.syllables)         # B
    sounds = score_sounds_base(expected, observed)           # B

    spans = align(audio, expected) if layers.ctc_spans else None            # C
    if layers.ctc_scores:
        sounds = score_sounds(audio, expected, spans)                       # C
    rhythm = score_rhythm(expected, spans) if layers.rhythm and spans else None                     # C
    tones = score_tones(audio, expected, spans) if layers.tone and (spans or len(expected) == 1) else None  # D

    return assemble(expected, observed, sounds, spans, rhythm, tones, transcript)   # B
```

`assemble` applies [scoring.md](scoring.md): syllable scores, statuses, the word roll-up, overall scores and feedback. It adds `audio.trim_offset_ms` to every time before returning it.

### Layer switches

`config.py` reads these environment variables. All default to off, so stage 1 runs with nothing set.

| Variable | Values | Effect |
|---|---|---|
| `GRADER` | `mock`, `real` | `mock` returns canned results without touching audio |
| `ENABLE_CTC` | `0`, `1` | Allows `align` and `score_sounds` to run |
| `ENABLE_RHYTHM` | `0`, `1` | Allows `score_rhythm` to run |
| `ENABLE_TONE` | `0`, `1` | Allows `score_tones` to run |

Experiments for manual testing, off by default. They are not part of the contract and may be removed:

| Variable | Values | Effect |
|---|---|---|
| `WHISPER_PROMPT` | text | Passed to Whisper as `initial_prompt`. A test found it made no difference to auto-correction (22 vs 23 of 45 mistakes kept). |
| `TONE_REFERENCE` | `0`, `1` | The tone check uses each word's reference clip in place of the expected tone's textbook shape (`score_tones_with_references`). |

With a switch on, `layers_for(target, mode, syllable_count)` applies this table. `syllable_count` selects the word-practice row; it is ignored for a line.

| Context | `ctc_spans` | `ctc_scores` | `rhythm` | `tone` |
|---|---|---|---|---|
| Line, spoken-accuracy mode | no | no | no | no |
| Line, singing-accuracy mode | yes | yes | yes | no |
| Word practice, one syllable | no | no | no | yes |
| Word practice, two or more syllables | yes | no | no | yes |

Checkpoint B can change a cell, for example turning `ctc_scores` off for singing-accuracy mode if only the boundaries prove reliable.

### When a layer fails

If `align`, `score_sounds`, `score_rhythm` or `score_tones` raises, or returns a list without exactly one entry per expected syllable, the grader logs the error and continues without that layer. Rhythm, and tone on a word of two or more syllables, need spans; when `align` is off or failed they are skipped. The attempt still returns a Whisper-base result, and `engine` reports what actually ran. A layer must never take the request down.

## 5. Integration rules

- **Stubs first.** At kickoff B commits `schemas.py` and a stub for every function in section 3, with the final signature and a body that raises `NotImplementedError`. Each owner replaces their own stubs. Imports work from the first hour.
- **Models load once.** Whisper and the CTC model are loaded at startup or on first use and kept in memory. No function loads a model per call.
- **Pure functions.** Every function in section 3 except `grade` depends only on its arguments. That is what lets each owner test alone.
- **Time budget.** A graded attempt should return within about 3 seconds on the demo Mac: Whisper up to 2 s, the CTC layer up to 1 s, tone and rhythm negligible. These are targets. Measured on an 11-core M-series Mac with a 1.4 s TTS line of 我想和你一起: `mlx-whisper` `large-v3-turbo` 0.63 s (under budget); `faster-whisper` `large-v3-turbo` ~5 s, `medium` ~3.6 s.
- **Changing a signature.** Edit this file first, tell the owners who call the function, then change the code.

## 6. Shared test data

Everyone tests against the same files, so results are comparable.

```text
backend/tests/fixtures/
├── lines/<name>.json                      # a Line object: the expected syllables
├── audio/<name>__<variant>__<speaker>.wav # a recording of that line
├── tone/<reading>__<variant>__<speaker>.wav  # a single word, for tone
├── session.py                             # the list of every recording, read by the tools below
├── prompts.py, prompts/                   # a clip to copy for each recording
└── check_recordings.py                    # checks names, format and what is still missing
```

- Audio is 16 kHz mono WAV.
- `<speaker>` is the recorder's first name in lowercase ASCII letters, so several people's takes of one item can sit side by side.
- Line `<variant>` says what the recording contains: `correct` (sung), `spoken` (said, not sung), `error-<index>-<expected>-<produced>` (one deliberate error at that syllable, such as `error-4-l-n`: syllable 4 said with n instead of l), `missing-<index>` (that syllable left out).
- Word `<reading>` is the word's `pinyin_numeric`, such as `xin1`. Its `<variant>` is `correct` or `said-tone<n>` (deliberately said with tone n).
- The full list, the prompts, and step-by-step instructions are in [docs/recording-session.md](../recording-session.md). Checkpoint B uses the line recordings.

## 7. Integration schedule

| When | From | To | What is handed over |
|---|---|---|---|
| Hour 1.5 | B | everyone | `schemas.py`, all stubs, the mock grader, the fixtures folder |
| Hour 2 | D | B | A working `to_syllables` |
| Hour 6 | D | B | A real `song.json` for song 1, loaded by the real grader (checkpoint A) |
| Hour 13 | C | B | `align` and `score_sounds` behind `ENABLE_CTC` (checkpoint B) |
| Hour 13 | C | D | Song 1's `song.json` with syllable times; spans available for tone |
| Hours 13–19 | C | B | `score_rhythm` behind `ENABLE_RHYTHM` |
| Hours 13–19 | D | B | `score_tones` behind `ENABLE_TONE` |
