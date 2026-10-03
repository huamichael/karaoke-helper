"""CTC layer: forced alignment and finer sound scores.

Provides align (the start and end of each expected syllable in the audio) and
score_sounds (compares each expected syllable with its confused variants on the
same audio). Runs on user recordings and, through align_track, on the original
song.

Owner: C. Spec: docs/contracts/backend-interfaces.md, section 3; docs/tasks/backend-ctc-rhythm.md.
"""

from __future__ import annotations

from app.schemas import Audio, SoundScore, Span, Syllable


def align(audio: Audio, expected: list[Syllable]) -> list[Span | None]:
    raise NotImplementedError


def score_sounds(audio: Audio, expected: list[Syllable], spans: list[Span | None]) -> list[SoundScore | None]:
    raise NotImplementedError
