"""Pure score_rhythm calculations, independent of audio and shared schemas.

The contract result models are still owned by B and are currently placeholders.
These tests exercise the numeric helper; public-result construction must be
covered after B lands RhythmResult and RhythmSyllable in app.schemas.
"""

from app.scoring.rhythm import _calculate_rhythm


def test_on_time_singing_ignores_start_offset_and_tempo() -> None:
    result = _calculate_rhythm(
        reference_times=[0, 500, 1000, 1500],
        user_times=[250, 850, 1450, 2050],
    )

    assert result == ([0, 0, 0, 0], [100, 100, 100, 100], 100)


def test_offsets_keep_early_and_late_direction_and_reduce_score() -> None:
    result = _calculate_rhythm(
        reference_times=[0, 1000, 2000, 3000],
        user_times=[100, 1100, 1900, 3100],
    )

    assert result is not None
    offsets, scores, line_score = result
    assert offsets == [20, 40, -140, 80]
    assert scores == [95, 90, 70, 82]
    assert line_score == 84


def test_linear_tempo_change_is_removed_by_fitted_slope() -> None:
    result = _calculate_rhythm(
        reference_times=[0, 1000, 2000, 3000],
        user_times=[500, 1700, 2900, 4100],
    )

    assert result == ([0, 0, 0, 0], [100, 100, 100, 100], 100)


def test_missing_times_keep_one_entry_per_reference_syllable() -> None:
    result = _calculate_rhythm(
        reference_times=[0, 1000, None, 3000, 4000],
        user_times=[250, 1250, 2250, 3250],
    )

    assert result == ([0, 0, None, 0, None], [100, 100, None, 100, None], 100)


def test_returns_none_without_reference_times_or_three_joint_alignments() -> None:
    assert _calculate_rhythm(
        reference_times=[None, None, None],
        user_times=[0, 1000, 2000],
    ) is None
    assert _calculate_rhythm(
        reference_times=[0, 1000, 2000],
        user_times=[0, None, 2000],
    ) is None
