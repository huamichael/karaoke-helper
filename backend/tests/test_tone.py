"""Tests for the pitch helper and score_tones.

Uses synthetic voices whose pitch follows each tone shape, at different voice
heights and pitch ranges. Real recordings are still needed to tune the
constants in app/scoring/tone.py.

Owner: D.
"""

import numpy as np
import pytest

from app.mandarin import to_syllables
from app.schemas import Audio, Span
from app.scoring.pitch import pitch_track
from app.scoring.tone import score_tones

SR = 16_000

# Pitch movement of each tone, in semitones from the speaker's base pitch.
SHAPES = {1: [0, 0, 0], 2: [-2, -1, 3], 3: [-1, -4, -4.5, 1], 4: [3, 0, -4]}
CHARACTERS = {1: "妈", 2: "麻", 3: "马", 4: "骂"}


def voice(base_hz: float, semitones: list[float], ms: int) -> np.ndarray:
    """A buzzy vowel-like sound whose pitch follows the given semitone points."""
    n = SR * ms // 1000
    points = [base_hz * 2 ** (s / 12) for s in semitones]
    f0 = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(points)), points)
    phase = 2 * np.pi * np.cumsum(f0) / SR
    wave = sum(np.sin(k * phase) / k for k in range(1, 12))
    fade = np.minimum(1, np.minimum(np.arange(n), n - np.arange(n)) / (SR * 0.02))
    return (0.3 * wave * fade).astype(np.float32)


def silence(ms: int) -> np.ndarray:
    return np.zeros(SR * ms // 1000, np.float32)


def recording(*parts: np.ndarray) -> Audio:
    return Audio(samples=np.concatenate(parts), sample_rate=SR, trim_offset_ms=0)


def test_pitch_track_is_relative_to_the_median():
    times, semitones = pitch_track(recording(silence(100), voice(200, [0, 0], 300), silence(100)).samples, SR)
    voiced = semitones[~np.isnan(semitones)]
    assert len(times) == len(semitones) and voiced.size > 20
    assert np.all(np.abs(voiced) < 0.5)
    assert np.isnan(semitones[0])  # leading silence is unvoiced


def test_pitch_track_too_short():
    times, semitones = pitch_track(np.zeros(100, np.float32), SR)
    assert times.size == 0 and semitones.size == 0


@pytest.mark.parametrize("base_hz", [110, 210], ids=["low voice", "high voice"])
@pytest.mark.parametrize("range_scale", [0.5, 1.0, 1.8], ids=["shallow", "normal", "wide"])
@pytest.mark.parametrize("tone", [1, 2, 3, 4])
def test_single_syllable_tone_recognised(tone, base_hz, range_scale):
    shape = [s * range_scale for s in SHAPES[tone]]
    [grade] = score_tones(recording(silence(150), voice(base_hz, shape, 380), silence(150)), to_syllables(CHARACTERS[tone]), None)
    assert grade.expected == tone and grade.heard == tone
    assert grade.score >= 80


def test_wrong_tone_capped():
    # 妈 (first tone) said with a falling fourth tone.
    [grade] = score_tones(recording(silence(150), voice(200, SHAPES[4], 380), silence(150)), to_syllables("妈"), None)
    assert (grade.expected, grade.heard) == (1, 4)
    assert grade.score <= 60


TWO_SYLLABLE_SPANS = [Span(start_ms=100, end_ms=400, confidence=1.0), Span(start_ms=460, end_ms=840, confidence=1.0)]


def two_syllables(first_tone: int, second_tone: int) -> Audio:
    return recording(
        silence(100),
        voice(180, [s + 2 for s in SHAPES[first_tone]], 300),
        silence(60),
        voice(180, SHAPES[second_tone], 380),
        silence(100),
    )


def test_two_syllables_use_sandhi():
    # 你好 is ni3 hao3, spoken ni2 hao3.
    grades = score_tones(two_syllables(2, 3), to_syllables("你好"), TWO_SYLLABLE_SPANS)
    assert [(g.expected, g.heard) for g in grades] == [(2, 2), (3, 3)]
    assert all(g.score >= 70 for g in grades)


def test_two_syllables_yi_sandhi():
    # 一片 is spoken yi2 pian4.
    grades = score_tones(two_syllables(2, 4), to_syllables("一片"), TWO_SYLLABLE_SPANS)
    assert [(g.expected, g.heard) for g in grades] == [(2, 2), (4, 4)]


def test_neutral_tone_not_scored():
    grades = score_tones(two_syllables(3, 1), to_syllables("我的"), TWO_SYLLABLE_SPANS)
    assert grades[1] is None and grades[0] is not None


def test_silence_has_no_heard_tone():
    [grade] = score_tones(recording(silence(500)), to_syllables("妈"), None)
    assert (grade.expected, grade.heard, grade.score) == (1, None, None)


def test_missing_span_has_no_heard_tone():
    grades = score_tones(two_syllables(2, 3), to_syllables("你好"), [TWO_SYLLABLE_SPANS[0], None])
    assert grades[1].heard is None and grades[1].score is None


def test_spans_required_for_longer_words():
    with pytest.raises(ValueError, match="one-syllable"):
        score_tones(two_syllables(2, 3), to_syllables("你好"), None)


def test_spans_must_match_syllables():
    with pytest.raises(ValueError, match="one entry per"):
        score_tones(two_syllables(2, 3), to_syllables("你好"), TWO_SYLLABLE_SPANS[:1])


# Tone feedback messages (the TONE_ rows in app/scoring/feedback.py)


def test_every_wrong_tone_has_its_own_message():
    from app.scoring.feedback import MESSAGES

    for expected in (1, 2, 3, 4):
        for heard in (1, 2, 3, 4):
            if heard != expected:
                assert f"TONE_{expected}_{heard}" in MESSAGES


def test_wrong_tone_feedback_reaches_the_learner():
    from app.schemas import Part, SoundScore, ToneGrade
    from app.scoring.feedback import MESSAGES, pick

    perfect = SoundScore(initial=Part(expected="x", heard="x", score=100), final=Part(expected="in", heard="in", score=100))
    feedback = pick(perfect, ToneGrade(expected=1, heard=4, score=40))
    assert feedback.code == "TONE_1_4" and feedback.message == MESSAGES["TONE_1_4"]
    assert pick(perfect, ToneGrade(expected=1, heard=1, score=95)) is None
