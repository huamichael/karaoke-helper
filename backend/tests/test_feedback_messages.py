"""Tests for the feedback messages in app/scoring/feedback.py.

A message is a hint on how to say the target syllable. It never says what the learner
said or why it was wrong, so the same syllable gets the same hint whatever was heard.
Codes, and which problem they record, are covered in test_grader.py.
"""

import pytest

from app.mandarin import to_syllables
from app.schemas import Part, SoundScore, ToneGrade
from app.scoring.feedback import ENDING_TIPS, GENERAL_TIP, INITIAL_TIPS, MESSAGES, TONE_TIPS, hint, pick


def attempt(expected_char: str, initial: str, final: str, tone: ToneGrade | None = None):
    """pick for one expected character when the grader heard initial + final."""
    s = to_syllables(expected_char)[0]
    has_initial = bool(s.initial or initial)
    sound = SoundScore(
        initial=Part(expected=s.initial, heard=initial, score=100 if initial == s.initial else 20) if has_initial else None,
        final=Part(expected=s.final, heard=final, score=100 if final == s.final else 20),
    )
    return pick(sound, tone, syllable=s)


WORDS_SPOKEN_TONE = lambda tone: ToneGrade(expected=tone, heard=tone, score=95)  # noqa: E731


def test_same_hint_whatever_was_heard():
    tone = WORDS_SPOKEN_TONE(1)
    messages = {
        attempt("心", "x", "i", tone).message,        # ending dropped
        attempt("心", "h", "ao", tone).message,       # a different syllable
        attempt("心", "s", "in", tone).message,       # wrong start
        attempt("心", "x", "in", ToneGrade(expected=1, heard=4, score=40)).message,  # wrong tone
        pick(None, ToneGrade(expected=1, heard=None, score=None), syllable=to_syllables("心")[0]).message,  # missing
    }
    assert messages == {hint("x", "in", 1)}


@pytest.mark.parametrize("char, initial, final", [
    ("你", "l", "i"), ("情", "q", "in"), ("心", "h", "ao"), ("我", "g", "uo"), ("是", "s", "i"), ("冷", "l", "uo"),
])
def test_message_makes_no_claim_about_the_attempt(char, initial, final):
    message = attempt(char, initial, final).message.lower()
    for claim in ("heard", "instead", "sounded", "rather than", "missing", "your pitch rose", "your pitch fell", "you said"):
        assert claim not in message
    assert message.startswith(f'how to say "{to_syllables(char)[0].pinyin}":')


def test_hint_for_xin_in_word_practice():
    assert hint("x", "in", 1) == ('How to say "xīn": ' + INITIAL_TIPS["x"] + " " + ENDING_TIPS["n"] + " " + TONE_TIPS[1])


def test_sung_line_hint_has_no_tone():
    # Tone is only graded in Word practice; in a sung line the melody replaces it.
    message = attempt("情", "q", "in").message
    assert message == 'How to say "qíng": ' + INITIAL_TIPS["q"] + " " + ENDING_TIPS["ng"]
    assert not any(tip in message for tip in TONE_TIPS.values())


def test_hint_uses_the_tone_after_sandhi():
    # 你 in 你好 is spoken ní; the tone grade carries the tone to speak.
    message = attempt("你", "n", "i", ToneGrade(expected=2, heard=3, score=40)).message
    assert message.startswith('How to say "ní":') and message.endswith(TONE_TIPS[2])


@pytest.mark.parametrize("char, tip", [
    ("是", 'The "i" after "sh" is a buzz'), ("字", 'The "i" after "z" is a buzz'),
    ("女", 'The "ü" here is "ee" said with rounded lips.'), ("去", 'The "u" here is "ee" said with rounded lips.'),
    ("的", 'The "e" is a relaxed "uh"'), ("想", ENDING_TIPS["ng"]),
])
def test_distinctive_sounds_get_a_tip(char, tip):
    s = to_syllables(char)[0]
    assert tip in hint(s.initial, s.final)


def test_a_syllable_with_nothing_distinctive_gets_the_general_tip():
    assert hint("", "a") == f'How to say "a": {GENERAL_TIP}'


def test_every_initial_has_a_tip():
    initials = {s.initial for c in "八怕妈发大他那拉嘎卡哈家掐虾扎插沙然杂擦撒" for s in to_syllables(c)}
    assert initials - {""} <= set(INITIAL_TIPS)


def test_without_the_expected_syllable_the_parts_are_used():
    sound = SoundScore(initial=Part(expected="n", heard="l", score=60), final=Part(expected="i", heard="i", score=100))
    assert pick(sound, None).message == hint("n", "i")
    assert pick(None, None).message == MESSAGES["MISSING"]


def test_rhythm_keeps_its_own_message():
    sound = SoundScore(initial=Part(expected="n", heard="n", score=100), final=Part(expected="i", heard="i", score=100))
    assert pick(sound, None, "RHYTHM_LATE").message == MESSAGES["RHYTHM_LATE"]
