# Task B: API and Whisper base

**Owner:** to be assigned. **Works alongside:** A (frontend), C (CTC and rhythm), D (songs and tone).

## Goal

You build the backend's spine: the HTTP API, the shared types, the Whisper base grader, and the orchestrator that C's and D's layers plug into. Your stage 1 output is the MVP. If nothing else ships, this does.

## Read first

1. [PROJECT_PLAN.md](../PROJECT_PLAN.md), sections 1, 2 and 4.
2. [contracts/api.md](../contracts/api.md): what you serve to the frontend.
3. [contracts/data-model.md](../contracts/data-model.md): the syllable record.
4. [contracts/backend-interfaces.md](../contracts/backend-interfaces.md): the functions you provide and call.
5. [contracts/scoring.md](../contracts/scoring.md): the rules `assemble` applies.

## What you own

```text
backend/pyproject.toml
backend/app/main.py            # routes
backend/app/schemas.py         # every shared type; you keep it, all three agree changes
backend/app/config.py          # layer switches
backend/app/audio.py           # load_audio
backend/app/songs.py           # load song bundles from data/songs/
backend/app/scoring/grader.py  # grade, assemble
backend/app/scoring/mock.py
backend/app/scoring/transcribe.py
backend/app/scoring/matcher.py # match, score_sounds_base
backend/app/scoring/confusions.py
backend/app/scoring/feedback.py
backend/tests/test_matcher.py, test_grader.py, test_api.py
```

C and D add their own dependencies to `pyproject.toml` and their own rows to `feedback.py`. Those are the only shared edits.

## What you use from others

| Function | Owner | Until it exists |
|---|---|---|
| `to_syllables` | D | Due at hour 2. Before that, test the matcher with hand-built `Syllable` objects. |
| `align`, `score_sounds`, `score_rhythm` | C | Your stubs raise `NotImplementedError`; the switches are off. |
| `score_tones` | D | Same. |
| `song.json` for song 1 | D | Use the two hand-written lines from kickoff. |

## Deliverables

### Kickoff, hours 0–1.5

1. `pyproject.toml` managed with `uv`: `fastapi`, `uvicorn`, `pydantic`, `python-multipart`, `faster-whisper`, `numpy`, `pytest`.
2. `schemas.py` with every type from the three contracts.
3. A stub for every function in backend-interfaces.md section 3, with the final signature.
4. The mock grader, selected by `GRADER=mock`.
5. The routes in api.md, CORS for `http://localhost:5173`, and static files under `/media`.
6. With D: `data/songs/demo/song.json` holding two hand-written lines.

**Done when:**
- `GET /api/v1/songs/demo` returns the fixture.
- `POST /api/v1/attempts` with any audio file returns a valid mock `AttemptResult`.
- A can generate TypeScript types from `/openapi.json`.

### Block 1, hours 1.5–6: the Whisper base

1. `load_audio`.
2. `transcribe`.
3. `match` and `score_sounds_base`.
4. `grade` and `assemble` for the Whisper base, for both `target=line` and `target=word`.
5. Feedback for missing syllables, initials and finals.
6. A test of Whisper on about 20 words spoken on their own. Write down how many came back correct, wrong and empty, and tell the team.

**Done when (checkpoint A):** with `GRADER=real`, on song 1, a sung line returns a grade per word, and a spoken word returns a grade.

### Block 2, hours 6–13

1. `config.py` with the switches and the `layers_for` table from backend-interfaces.md section 4.
2. Save every attempt: `data/attempts/<attempt_id>.wav` and `<attempt_id>.json`.
3. The full feedback catalogue for the confused pairs.
4. Call C's `align` and `score_sounds` behind `ENABLE_CTC`, with the fall-back-on-failure rule.
5. Help A with integration.

**Done when:** flipping `ENABLE_CTC=1` changes `engine` to `whisper+ctc` and fills `timing` in singing-accuracy mode, and a failure inside C's code still returns a Whisper-base result.

### Block 3, hours 13–19

1. Call `score_rhythm` and `score_tones` behind their switches.
2. Apply whatever checkpoint B decides to the `layers_for` table.
3. Tune thresholds on the saved attempts. Fix bugs.

## Implementation notes

### Audio

- Decode with `faster_whisper.decode_audio(file_like, sampling_rate=16000)`. It handles webm/opus and returns float32 mono, with no system ffmpeg needed.
- Trim silence with a simple energy threshold. Keep 150 ms on each side. Record what you cut from the start in `trim_offset_ms`.
- Reject recordings longer than 30 seconds.

### Whisper

- Load one model at startup: `WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")`. If it is too slow on the demo Mac, try `medium`.
- Call it with `language="zh"`, `beam_size=5`, `temperature=0.0`, `condition_on_previous_text=False`, and no `initial_prompt`.
- Never pass the expected lyric as a prompt. It biases the transcript toward a pass.
- `vad_filter=True` reduces invented text on silence, but it may drop a very short word. Test both settings on the isolated words.
- Whisper may return Traditional characters. That is fine: `to_syllables` handles both scripts and you compare sounds, not characters.
- Set `tone=None` on every syllable in the transcript. Whisper does not measure tone.

### Matcher

- Use global sequence alignment (Needleman–Wunsch) over syllables.
- Suggested starting costs: 0 when initial and final both match; 1 when each differs by at most a confused pair; 2 otherwise; 1.5 for a gap.
- If the heard `hanzi` equals the expected `hanzi`, treat it as a full match and copy the expected reading into the observed syllable.
- Extra heard syllables are dropped. Unmatched expected syllables become `None`.

Test cases for `test_matcher.py`, none of which need audio. The expected line is 我想和你一起.

| Heard | Expected outcome |
|---|---|
| 我想和你一起 | Every syllable matched; every component 100 |
| 我想和李一起 | 你: initial n/l scores 60, final 100 |
| 我想和泥一起 | 你: full match (same sound, different character) |
| 我想你一起 | `observed[2]` (和) is `None`; the rest matched |
| 我想和你啊一起 | The extra 啊 is dropped; every expected syllable matched |
| (empty) | `no_speech` |

### Grader

- `assemble` follows scoring.md exactly. Do not put thresholds anywhere else.
- `engine` reports what actually ran: `mock`, `whisper`, or `whisper+ctc`.
- Add `audio.trim_offset_ms` to every time you return.
- `next_step`: suggest `practice_word` for the lowest-scoring word that is not `good`; `retry_line` when completeness is under 50; otherwise `next_line`.

### Mock grader

- Build the result from the line's own syllables, so every field is valid.
- Make it deterministic and varied: cycle the statuses good, good, ok, good, wrong, good, missing across syllables, shifted by `line_index`. A sees every colour.
- Return `no_speech` when the uploaded file is smaller than 2 KB.

### Running

```bash
cd backend
uv sync
GRADER=mock uv run uvicorn app.main:app --reload --port 8000
uv run pytest
```

## Out of scope

- Accounts, a database, user history.
- The internals of the CTC layer, rhythm and tone. You call them; you do not write them.
- The song pipeline.
