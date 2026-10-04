"""Rhythm scoring after removing start offset and tempo (owner C)."""

from __future__ import annotations

from math import exp
from typing import Sequence

from app.schemas import RhythmResult, RhythmSyllable, Span, Syllable


def _calculate_rhythm(
    reference_times: Sequence[int | None],
    user_times: Sequence[int | None],
) -> tuple[list[int | None], list[int | None], int] | None:
    """Fit tempo and start time, returning aligned offsets, scores, and mean.

    The two returned per-syllable lists have the same length as
    ``reference_times``. An index is ``None`` when either time is unavailable.
    """
    paired = [
        (index, reference_time, user_times[index])
        for index, reference_time in enumerate(reference_times)
        if reference_time is not None
        and index < len(user_times)
        and user_times[index] is not None
    ]
    if len(paired) < 3:
        return None

    x_values = [float(reference_time) for _, reference_time, _ in paired]
    y_values = [float(user_time) for _, _, user_time in paired]
    mean_x = sum(x_values) / len(x_values)
    mean_y = sum(y_values) / len(y_values)
    variance_x = sum((value - mean_x) ** 2 for value in x_values)

    if variance_x == 0:
        return None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values)) / variance_x
    intercept = mean_y - slope * mean_x

    offsets: list[int | None] = [None] * len(reference_times)
    scores: list[int | None] = [None] * len(reference_times)
    for index, reference_time, user_time in paired:
        residual_ms = float(user_time) - (intercept + slope * float(reference_time))
        offset_ms = round(residual_ms)
        offsets[index] = offset_ms
        scores[index] = round(100 * exp(-abs(offset_ms) / 400))

    usable_scores = [score for score in scores if score is not None]
    line_score = round(sum(usable_scores) / len(usable_scores))
    return offsets, scores, line_score


def score_rhythm(
    reference: list[Syllable], spans: list[Span | None]
) -> RhythmResult | None:
    """Compare syllable onsets after removing the tempo and starting offset.

    Returns ``None`` when fewer than three syllables have both reference and
    user onset times. Otherwise, the result contains one entry per reference
    syllable, with ``None`` for an unavailable onset.
    """
    reference_times = [syllable.start_ms for syllable in reference]
    user_times = [
        spans[index].start_ms
        if index < len(spans) and spans[index] is not None
        else None
        for index in range(len(reference))
    ]
    calculation = _calculate_rhythm(reference_times, user_times)
    if calculation is None:
        return None

    offsets, scores, line_score = calculation

    syllables = [
        None
        if offset is None or score is None
        else RhythmSyllable(offset_ms=offset, score=score)
        for offset, score in zip(offsets, scores)
    ]
    return RhythmResult(score=line_score, syllables=syllables)
