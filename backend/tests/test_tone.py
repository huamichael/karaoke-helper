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
from app.scoring.tone import score_tones, score_tones_with_references, syllable_contours

SR = 16_000

# Pitch movement of each tone, in semitones from the speaker's base pitch.
SHAPES: dict[int, list[float]] = {1: [0, 0, 0], 2: [-2, -1, 3], 3: [-1, -4, -4.5, 1], 4: [3, 0, -4]}
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


# The CTC layer marks only the start of each syllable, not the whole of it.
SHORT_SPANS = [Span(start_ms=100, end_ms=160, confidence=1.0), Span(start_ms=460, end_ms=520, confidence=1.0)]


@pytest.mark.parametrize("first, second, text", [(2, 4, "一片"), (4, 4, "爱慕")])
def test_short_spans_read_each_syllable_up_to_the_next(first, second, text):
    grades = score_tones(two_syllables(first, second), to_syllables(text), SHORT_SPANS)
    assert [(g.expected, g.heard) for g in grades] == [(first, first), (second, second)]


def test_last_syllable_stops_after_its_own_length():
    # 爱慕 then, 60 ms later, a rising sound that is not part of the word.
    audio = recording(two_syllables(4, 4).samples[:-SR // 10], silence(60), voice(180, SHAPES[2], 300), silence(100))
    grades = score_tones(audio, to_syllables("爱慕"), SHORT_SPANS)
    assert [(g.expected, g.heard) for g in grades] == [(4, 4), (4, 4)]


def test_syllable_before_a_missing_one_stops_after_its_own_length():
    # 爱慕慕 with the middle syllable said rising and not placed by the CTC layer.
    audio = recording(two_syllables(4, 4).samples[:SR * 400 // 1000], voice(180, [-4, 0, 6], 500), silence(60),
                      voice(180, SHAPES[4], 380), silence(100))
    spans = [SHORT_SPANS[0], None, Span(start_ms=960, end_ms=1020, confidence=1.0)]
    grades = score_tones(audio, to_syllables("爱慕慕"), spans)
    assert (grades[0].expected, grades[0].heard) == (4, 4) and grades[0].score >= 80
    assert grades[1].heard is None


def level_syllables(count: int) -> tuple[Audio, list[Span]]:
    """count level syllables at 200 Hz, 280 ms long with 60 ms gaps: a robotic voice."""
    parts = [p for _ in range(count) for p in (voice(200, [0, 0, 0], 280), silence(60))]
    spans = [Span(start_ms=100 + k * 340, end_ms=100 + k * 340 + 80, confidence=1.0) for k in range(count)]
    return recording(silence(100), *parts, silence(40)), spans


def test_level_syllable_at_middle_height_is_first_tone():
    grades = score_tones(two_syllables(4, 1), to_syllables("大家"), TWO_SYLLABLE_SPANS)
    assert [(g.expected, g.heard) for g in grades] == [(4, 4), (1, 1)]


def test_low_flat_third_tone_inside_a_word_is_heard_by_its_height():
    # 雨天: 雨 is often said low and flat inside a word. Only its height tells it from a first tone.
    audio = recording(silence(100), voice(200 * 2 ** (-6 / 12), [0, 0, 0], 300), silence(60),
                      voice(200, [0, 0, 0], 380), silence(100))
    grades = score_tones(audio, to_syllables("雨天"), TWO_SYLLABLE_SPANS)
    assert [(g.expected, g.heard) for g in grades] == [(3, 3), (1, 1)]


def test_robotic_voice_hears_level_tones_and_marks_others_wrong():
    audio, spans = level_syllables(4)
    grades = score_tones(audio, to_syllables("你問我愛"), spans)
    assert [g.heard for g in grades] == [1, 1, 1, 1]
    assert all(g.score <= 60 for g in grades)


# TONE_REFERENCE experiment: the reference clip's contour stands in for the expected shape.


def test_reference_contour_replaces_the_expected_shape():
    # 骂 said with a dip, and a reference clip that dips the same way.
    dip = recording(silence(150), voice(200, SHAPES[3], 380), silence(150))
    reference = syllable_contours(dip, to_syllables("骂"), None)
    [plain] = score_tones(dip, to_syllables("骂"), None)
    [with_reference] = score_tones_with_references(dip, to_syllables("骂"), None, reference)
    assert (plain.expected, plain.heard) == (4, 3)
    assert (with_reference.expected, with_reference.heard) == (4, 4) and with_reference.score >= 95


def test_missing_reference_falls_back_to_the_textbook_shape():
    flat = recording(silence(150), voice(200, [0, 0, 0], 380), silence(150))
    assert score_tones_with_references(flat, to_syllables("骂"), None, [None]) == score_tones(flat, to_syllables("骂"), None)


def test_references_must_match_syllables():
    with pytest.raises(ValueError, match="one entry per"):
        score_tones_with_references(two_syllables(2, 3), to_syllables("你好"), TWO_SYLLABLE_SPANS, [None])


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
