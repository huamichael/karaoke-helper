"""Rhythm scoring and grader integration with the real shared models."""
import numpy as np
import pytest

from app.schemas import Audio, RhythmResult, RhythmSyllable, Span, Syllable, Transcript, ToneGrade
from app.scoring import feedback, grader
from app.scoring.rhythm import _calculate_rhythm, score_rhythm
from tests.test_ctc import song_bundle


def syllables(times):
    return [Syllable(hanzi="啊", pinyin="ā", pinyin_numeric="a1", initial="", final="a",
                     tone=1, start_ms=t, end_ms=None) for t in times]


def spans(times):
    return [None if t is None else Span(start_ms=t, end_ms=t + 100, confidence=1) for t in times]


def test_on_time_singing_ignores_start_offset_and_tempo():
    result = score_rhythm(syllables([0, 500, 1000, 1500]), spans([250, 850, 1450, 2050]))
    assert result == RhythmResult(score=100, syllables=[RhythmSyllable(offset_ms=0, score=100)] * 4)


def test_offsets_keep_early_and_late_direction_and_reduce_score():
    result = score_rhythm(syllables([0, 1000, 2000, 3000]), spans([100, 1100, 1900, 3100]))
    assert [s.offset_ms for s in result.syllables] == [20, 40, -140, 80]
    assert [s.score for s in result.syllables] == [95, 90, 70, 82]
    assert result.score == 84


def test_missing_times_keep_one_entry_per_reference_syllable():
    result = score_rhythm(syllables([0, 1000, None, 3000, 4000]), spans([250, 1250, 2250, 3250]))
    assert len(result.syllables) == 5
    assert result.syllables[2] is None and result.syllables[4] is None
    assert result.score == 100


@pytest.mark.parametrize("reference,user", [
    ([None, None, None], [0, 1000, 2000]), ([0, 1000, 2000], [0, None, 2000]),
    ([0, 0, 0], [0, 1000, 2000]), ([], []),
])
def test_unavailable_reference_or_alignment_gets_no_score(reference, user):
    assert score_rhythm(syllables(reference), spans(user)) is None


def test_two_rushed_syllables_reduce_line_score():
    reference = syllables([0, 1000, 2000, 3000, 4000, 5000])
    regular = score_rhythm(reference, spans([250, 1250, 2250, 3250, 4250, 5250]))
    rushed = score_rhythm(reference, spans([250, 1250, 1750, 2750, 4250, 5250]))
    assert regular.score == 100 and rushed.score < 75


def test_calculation_does_not_change_inputs():
    reference, user = [0, 1000, 2000], [500, 1700, 2900]
    assert _calculate_rhythm(reference, user) == ([0, 0, 0], [100, 100, 100], 100)
    assert reference == [0, 1000, 2000] and user == [500, 1700, 2900]


@pytest.fixture
def grading(monkeypatch):
    line = song_bundle().lines[0]
    for i, s in enumerate(line.syllables):
        s.start_ms = i * 1000
    transcript = Transcript(text=line.text, syllables=line.syllables, no_speech=False)
    monkeypatch.setattr(grader, "transcribe", lambda _: transcript)
    monkeypatch.setattr(grader, "score_sounds", lambda a, expected, sp: grader.score_sounds_base(expected, expected))
    monkeypatch.setattr(grader, "align", lambda a, expected: spans([100, 1100, 1600, 2600, 4100, 5100, 6100]))
    for flag in ("ENABLE_CTC", "ENABLE_RHYTHM"):
        monkeypatch.setenv(flag, "1")
    monkeypatch.setenv("ENABLE_TONE", "0")
    recording = Audio(np.ones(16000, dtype=np.float32), 16000, 150)
    return line, recording


def test_rhythm_switch_reaches_api_result_and_good_pronunciation_feedback(grading):
    line, recording = grading
    result = grader.grade(recording, line, "line", "singing", None)
    assert result.scores.rhythm < 100 and result.scores.overall < 100
    assert result.syllables[2].score == 100
    assert result.syllables[2].status == "wrong"
    assert result.syllables[2].feedback.code == "RHYTHM_EARLY"
    assert result.syllables[2].timing.start_ms == 1750


def test_spoken_and_disabled_rhythm_do_not_call_scorer(monkeypatch, grading):
    line, recording = grading
    monkeypatch.setattr(grader, "score_rhythm", lambda *_: pytest.fail("unexpected rhythm call"))
    assert grader.grade(recording, line, "line", "spoken", None).scores.rhythm is None
    monkeypatch.setenv("ENABLE_RHYTHM", "0")
    assert grader.grade(recording, line, "line", "singing", None).scores.rhythm is None


def test_rhythm_failure_preserves_pronunciation(monkeypatch, grading):
    line, recording = grading
    monkeypatch.setattr(grader, "score_rhythm", lambda *_: (_ for _ in ()).throw(RuntimeError("rhythm failed")))
    result = grader.grade(recording, line, "line", "singing", None)
    assert result.scores.rhythm is None and result.scores.overall == 100


def test_feedback_prioritizes_pronunciation_then_tone_then_rhythm():
    sound = grader.score_sounds_base(syllables([0]), syllables([0]))[0]
    rhythm = RhythmSyllable(offset_ms=200, score=61)
    code = grader._rhythm_code(rhythm)
    assert feedback.pick(sound, None, code).code == "RHYTHM_LATE"
    assert feedback.pick(sound, ToneGrade(expected=1, heard=2, score=40), code).code == "TONE_1_2"
    assert feedback.pick(None, None, code).code == "MISSING"
    sound.final.score = 40
    assert feedback.pick(sound, None, code).code == "FINAL_OTHER"
    assert "could not hear" in feedback.pick(sound, None).message
