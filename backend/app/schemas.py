"""Every shared type, in one place.

Holds the syllable record and song bundle (Syllable, LyricSyllable, Word, Line,
Song), the API result types (AttemptResult and its parts), and the types passed
between backend layers (Audio, Transcript, Span, SoundScore, ToneGrade,
RhythmResult). This file is the contracts in executable form: change the contract
document first, then this file.

Keeper: B. Spec: docs/contracts/data-model.md, api.md and backend-interfaces.md.
"""

from dataclasses import dataclass
from typing import Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

Score = Annotated[int, Field(ge=0, le=100)] | None
Tone = Annotated[int, Field(ge=1, le=5)] | None
Status = Literal["good", "ok", "wrong", "missing"]
Target = Literal["line", "word"]
Mode = Literal["spoken", "singing"]


class _Model(BaseModel):
    # Unknown fields fail loudly, so a typo in song.json or a layer's output is caught.
    model_config = ConfigDict(extra="forbid")


# --- Syllable record and song bundle: data-model.md -------------------------


class Syllable(_Model):
    hanzi: str
    pinyin: str
    pinyin_numeric: str
    initial: str
    final: str
    tone: Tone
    start_ms: int | None
    end_ms: int | None


class LyricSyllable(Syllable):
    tone: Annotated[int, Field(ge=1, le=5)]
    index: int
    word_index: int


class Word(_Model):
    index: int
    text: str
    syllable_indices: list[int]
    gloss: str | None
    audio_url: str | None


class Line(_Model):
    index: int
    start_ms: int
    end_ms: int
    text: str
    translation: str | None
    syllables: list[LyricSyllable]
    words: list[Word]


class SongSummary(_Model):
    id: str
    title: str
    artist: str
    line_count: int


class Song(_Model):
    id: str
    title: str
    artist: str
    line_count: int
    audio_url: str
    # The track without its singer, for Karaoke mode; None until pipeline.instrumental makes it.
    instrumental_url: str | None = None
    lines: list[Line]


# --- Types passed between backend layers: backend-interfaces.md section 2 ---


@dataclass
class Audio:
    samples: np.ndarray
    sample_rate: int
    trim_offset_ms: int


class Transcript(_Model):
    text: str
    syllables: list[Syllable]
    no_speech: bool


class Span(_Model):
    start_ms: int
    end_ms: int
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]


class Part(_Model):
    expected: str
    heard: str | None
    score: Score


class SoundScore(_Model):
    initial: Part | None
    final: Part


class ToneGrade(_Model):
    expected: int
    heard: int | None
    score: Score


class RhythmSyllable(_Model):
    offset_ms: int
    score: Annotated[int, Field(ge=0, le=100)]


class RhythmResult(_Model):
    score: Annotated[int, Field(ge=0, le=100)]
    syllables: list[RhythmSyllable | None]


# --- API result types: api.md -----------------------------------------------


class Scores(_Model):
    overall: Score
    pronunciation: Score
    completeness: Score
    rhythm: Score
    tone: Score
    melody: Score


class WordResult(_Model):
    index: int
    text: str
    pinyin: str
    status: Status             # pronunciation only, in both modes; rhythm never changes it
    score: Score
    syllable_indices: list[int]
    # RHYTHM MARKER (disabled; see _word_rhythm in app/scoring/grader.py):
    # rhythm: Literal["early", "late", "on_time"] | None = None  # singing mode only; None elsewhere


class Timing(_Model):
    start_ms: int
    end_ms: int
    offset_ms: int | None
    score: Score


class Feedback(_Model):
    code: str
    message: str


class SyllableResult(_Model):
    index: int
    hanzi: str
    pinyin: str
    status: Status
    score: Score
    initial: Part | None
    final: Part | None
    tone: ToneGrade | None
    timing: Timing | None
    feedback: Feedback | None


class Heard(_Model):
    hanzi: str
    pinyin: str


class PracticeWordStep(_Model):
    type: Literal["practice_word"]
    word_index: int
    message: str


class LineStep(_Model):
    type: Literal["retry_line", "next_line"]
    message: str


NextStep = Annotated[PracticeWordStep | LineStep, Field(discriminator="type")]


class AttemptResult(_Model):
    attempt_id: str
    song_id: str
    line_index: int
    word_index: int | None
    target: Target
    mode: Mode | None
    status: Literal["ok", "no_speech"]
    engine: str
    scores: Scores
    words: list[WordResult]
    syllables: list[SyllableResult]
    heard: Heard | None
    next_step: NextStep


class Health(_Model):
    status: Literal["ok"]
    grader: Literal["mock", "real"]


class ErrorDetail(_Model):
    code: str
    message: str


class ErrorBody(_Model):
    error: ErrorDetail
