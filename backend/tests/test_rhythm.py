"""Rhythm scoring tests, independent from audio and model loading."""

from dataclasses import dataclass
from types import SimpleNamespace

import app.schemas as schemas
from app.scoring.rhythm import _calculate_rhythm, score_rhythm


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


@dataclass
class _FakeRhythmSyllable:
    offset_ms: int
    score: int


@dataclass
class _FakeRhythmResult:
    score: int
    syllables: list[_FakeRhythmSyllable | None]


def _syllable(start_ms: int | None) -> SimpleNamespace:
    return SimpleNamespace(start_ms=start_ms)


def _span(start_ms: int | None) -> SimpleNamespace | None:
    return None if start_ms is None else SimpleNamespace(start_ms=start_ms)


def _install_fake_result_types(monkeypatch) -> None:
    """Use lightweight contract-shaped models while B's schemas are stubs."""
    monkeypatch.setattr(schemas, "RhythmSyllable", _FakeRhythmSyllable, raising=False)
    monkeypatch.setattr(schemas, "RhythmResult", _FakeRhythmResult, raising=False)


def test_public_score_rhythm_removes_start_offset_and_tempo(monkeypatch) -> None:
    _install_fake_result_types(monkeypatch)

    result = score_rhythm(
        [_syllable(t) for t in [0, 500, 1000, 1500]],
        [_span(t) for t in [250, 850, 1450, 2050]],
    )

    assert result == _FakeRhythmResult(
        score=100,
        syllables=[_FakeRhythmSyllable(offset_ms=0, score=100) for _ in range(4)],
    )


def test_public_score_rhythm_preserves_one_entry_per_reference_syllable(monkeypatch) -> None:
    _install_fake_result_types(monkeypatch)

    result = score_rhythm(
        [_syllable(t) for t in [0, 1000, None, 3000, 4000]],
        [_span(t) for t in [250, 1250, 2250, 3250]],
    )

    assert result is not None
    assert len(result.syllables) == 5
    assert result.syllables[2] is None
    assert result.syllables[4] is None
    assert result.score == 100


def test_public_score_rhythm_returns_none_with_fewer_than_three_joint_times(
    monkeypatch,
) -> None:
    _install_fake_result_types(monkeypatch)

    result = score_rhythm(
        [_syllable(t) for t in [0, 1000, 2000]],
        [_span(t) for t in [0, None, 2000]],
    )

    assert result is None


def test_public_score_rhythm_keeps_early_and_late_offset_signs(monkeypatch) -> None:
    _install_fake_result_types(monkeypatch)

    result = score_rhythm(
        [_syllable(t) for t in [0, 1000, 2000, 3000]],
        [_span(t) for t in [100, 1100, 1900, 3100]],
    )

    assert result is not None
    assert [item.offset_ms for item in result.syllables] == [20, 40, -140, 80]
    assert [item.score for item in result.syllables] == [95, 90, 70, 82]
    assert result.score == 84
