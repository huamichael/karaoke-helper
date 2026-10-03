# Contract: data model

**Keeper:** B (the code in `backend/app/schemas.py`). **Used by:** everyone.

This file defines the one structure that every part of the system uses for Mandarin text and audio timing: the **syllable record**. Song processing and user-input processing both produce it, so anything can be compared with anything else field by field.

## 1. The syllable record

```python
# backend/app/schemas.py
class Syllable(BaseModel):
    hanzi: str               # one character: "你"
    pinyin: str              # with tone mark, for display: "nǐ"
    pinyin_numeric: str      # ASCII with tone digit: "ni3"
    initial: str             # opening consonant: "n". "" when there is none
    final: str               # the rest of the syllable: "i"
    tone: int | None         # 1-4, or 5 for neutral. None = not known
    start_ms: int | None     # start within its own audio. None = not aligned
    end_ms: int | None       # end within its own audio. None = not aligned
```

A lyric line, a word, and a user's attempt are each a `list[Syllable]`, in order. One Hanzi character is always exactly one syllable.

## 2. Conventions

Only one function creates syllable records from text: `to_syllables()` in `backend/app/mandarin.py` (owner: D). Nobody else calls pypinyin directly, so these conventions hold everywhere by construction.

- **Initials and finals** follow pypinyin's strict mode. `y` and `w` are not initials, and finals are written in full.
- **ü** is written `ü` in `pinyin` and `v` in `pinyin_numeric`, `initial` and `final`.
- **Neutral tone** is 5.
- **Non-Hanzi characters** (punctuation, Latin letters, spaces) are dropped. They produce no syllable.
- **Times** are integer milliseconds from the start of the audio the syllable belongs to (section 3).

Examples, checked against pypinyin 0.55:

| Hanzi | `pinyin` | `pinyin_numeric` | `initial` | `final` | `tone` |
|---|---|---|---|---|---|
| 我 | wǒ | wo3 | (empty) | uo | 3 |
| 想 | xiǎng | xiang3 | x | iang | 3 |
| 一 (in 一起) | yì | yi4 | (empty) | i | 4 |
| 就 | jiù | jiu4 | j | iou | 4 |
| 会 | huì | hui4 | h | uei | 4 |
| 准 | zhǔn | zhun3 | zh | uen | 3 |
| 女 | nǚ | nv3 | n | v | 3 |
| 月 | yuè | yue4 | (empty) | ve | 4 |
| 的 | de | de5 | d | e | 5 |

## 3. Two producers, one structure

```text
Song processing (ahead of time)          User input processing (per attempt)
-------------------------------          -----------------------------------
lyric text                               recording
  -> to_syllables()        [D]             -> transcribe()          [B]
  -> align_track()         [C]             -> match()               [B]
                                           -> align()               [C]
                                           -> score_tones()         [D]
= reference: list[Syllable]              = observed: list[Syllable | None]
  times measured in the track              times measured in the recording
```

| Field | Reference syllable (from the song) | Observed syllable (from the user) |
|---|---|---|
| `hanzi` | The lyric character | The character Whisper transcribed |
| `pinyin`, `pinyin_numeric`, `initial`, `final` | The verified reading, after hand corrections | The dictionary reading of the transcribed character. With the CTC layer on, `initial` and `final` are what CTC heard. |
| `tone` | The lexical tone of the verified reading | `None` until the tone layer measures it. Never taken from Whisper's character. |
| `start_ms`, `end_ms` | Position in the song track, filled by `align_track`. `None` until then. | Position in the user's recording, filled by `align`. `None` when the CTC layer did not run. |

The functions named here are specified in [backend-interfaces.md](backend-interfaces.md).

## 4. The index rule

After processing, the user's attempt has the same shape as the lyric it was graded against:

- `expected` is the reference `list[Syllable]` for the line or word.
- `observed` is a `list[Syllable | None]` of the **same length and order**. `observed[i]` is what the user produced for `expected[i]`, or `None` if it is missing.

Every score is then a comparison of `expected[i]` with `observed[i]`:

| Score | Fields compared |
|---|---|
| Pronunciation | `initial` and `final` |
| Completeness | whether `observed[i]` is `None` |
| Tone | `tone` |
| Rhythm | `start_ms`, each measured from the start of its own line |

Every layer's per-syllable output follows the same rule: one entry per expected syllable, in order.

## 5. The song bundle

The lyric side extends the syllable record with its position in the line:

```python
class LyricSyllable(Syllable):
    index: int               # position within the line, from 0
    word_index: int          # which word of the line it belongs to

class Word(BaseModel):
    index: int
    text: str                # "一起"
    syllable_indices: list[int]
    gloss: str | None        # English meaning
    audio_url: str | None    # spoken reference clip

class Line(BaseModel):
    index: int
    start_ms: int            # position in the track
    end_ms: int
    text: str                # Hanzi
    translation: str | None
    syllables: list[LyricSyllable]
    words: list[Word]

class Song(BaseModel):
    id: str
    title: str
    artist: str
    line_count: int
    audio_url: str
    lines: list[Line]
```

`song.json` on disk is exactly one `Song` object. The same object is what `GET /api/v1/songs/{id}` returns ([api.md](api.md)). The pipeline's output, the backend's input and the frontend's input are one format.

```text
data/songs/<song_id>/
├── song.json        # a Song object
├── overrides.json   # readings corrected by hand; input to the pipeline
├── audio.mp3        # the track
└── words/           # spoken clip per word: <line_index>_<word_index>.mp3
```

Two pipeline steps write `song.json`:

| Step | Owner | Fills |
|---|---|---|
| `build_song` | D | Everything except syllable `start_ms` and `end_ms`, which stay `None` |
| `align_track` | C | Syllable `start_ms` and `end_ms`, using the same `align()` that runs on user recordings |

## 6. Worked example

The lyric is 我想和你一起. The user sang 你 closer to "lǐ". Only that syllable is shown.

Reference, from `song.json` after both pipeline steps:

```json
{ "index": 3, "word_index": 3,
  "hanzi": "你", "pinyin": "nǐ", "pinyin_numeric": "ni3",
  "initial": "n", "final": "i", "tone": 3,
  "start_ms": 17840, "end_ms": 18210 }
```

Observed, Whisper base only:

```json
{ "hanzi": "李", "pinyin": "lǐ", "pinyin_numeric": "li3",
  "initial": "l", "final": "i", "tone": null,
  "start_ms": null, "end_ms": null }
```

Observed, with the CTC layer on:

```json
{ "hanzi": "李", "pinyin": "lǐ", "pinyin_numeric": "li3",
  "initial": "l", "final": "i", "tone": null,
  "start_ms": 1830, "end_ms": 2210 }
```

Comparing `initial` gives "expected n, heard l". Comparing `start_ms` against the reference, each measured from its line start, gives the rhythm offset.
