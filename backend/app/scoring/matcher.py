"""Whisper base, step 2: line up what was heard against what was expected.

Provides match (sequence-aligns the heard syllables to the expected ones and
returns one observed syllable, or None, per expected syllable) and
score_sounds_base (the 100 / 60 / 20 component scores for initials and finals).

Owner: B. Spec: docs/contracts/scoring.md.
"""

from __future__ import annotations

from app.schemas import SoundScore, Syllable


def match(expected: list[Syllable], heard: list[Syllable]) -> list[Syllable | None]:
    raise NotImplementedError


def score_sounds_base(expected: list[Syllable], observed: list[Syllable | None]) -> list[SoundScore | None]:
    raise NotImplementedError
