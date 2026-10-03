"""Rhythm score for singing-accuracy mode.

Provides score_rhythm: compares the user's syllable start times with the original
singer's after removing tempo and starting point, and returns a score for each
syllable and for the line.

Owner: C. Spec: docs/contracts/scoring.md.
"""

from __future__ import annotations

from app.schemas import RhythmResult, Span, Syllable


def score_rhythm(reference: list[Syllable], spans: list[Span | None]) -> RhythmResult | None:
    raise NotImplementedError
