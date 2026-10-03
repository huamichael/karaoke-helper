"""Lexical tone score for Word practice.

Provides score_tones: compares the pitch contour inside each syllable with the
four standard tone shapes and returns the expected tone, the heard tone and a
score. Never used on sung lines.

Owner: D. Spec: docs/contracts/scoring.md.
"""

from __future__ import annotations

from app.schemas import Audio, Span, Syllable, ToneGrade


def score_tones(audio: Audio, expected: list[Syllable], spans: list[Span | None] | None) -> list[ToneGrade | None]:
    raise NotImplementedError
