"""Tests for grade and assemble.

Covers syllable scores, statuses, the word roll-up, overall scores, and falling
back to the Whisper base when a layer fails. Expected numbers are worked out by
hand from scoring.md; the n/l case is api.md's example result.

Owner: B. Spec: docs/contracts/scoring.md.
"""

import numpy as np
import pytest

from app.schemas import (
    Audio, Line, LyricSyllable, Part, RhythmResult, RhythmSyllable, SoundScore, Span, ToneGrade, Transcript, Word,
)
from app.scoring import feedback, grader
from tests.test_matcher import READINGS, sylls
from tests.test_schemas import EXAMPLE_RESULT

AUDIO = Audio(samples=np.zeros(16000, dtype=np.float32), sample_rate=16000, trim_offset_ms=0)


def make_line(words: list[str], index: int = 0) -> Line:
    syllables, word_objs, i = [], [], 0
    for w_idx, word in enumerate(words):
        indices = []
        for ch in word:
            p, n, ini, fin, tone = READINGS[ch]
            syllables.append(LyricSyllable(index=i, word_index=w_idx, hanzi=ch, pinyin=p, pinyin_numeric=n,
                                           initial=ini, final=fin, tone=tone, start_ms=None, end_ms=None))
            indices.append(i)
            i += 1
        word_objs.append(Word(index=w_idx, text=word, syllable_indices=indices, gloss=None, audio_url=None))
    return Line(index=index, start_ms=0, end_ms=5000, text="".join(words), translation=None,
                syllables=syllables, words=word_objs)


LINE = make_line(["我", "想", "和", "你", "一起"])


def heard(text: str) -> Transcript:
    return Transcript(text=text, syllables=sylls(text, heard=True), no_speech=not text)


def run(monkeypatch, said: str, line: Line = LINE, target="line", mode="spoken", word_index=None, audio=AUDIO):
    monkeypatch.setattr(grader, "transcribe", lambda _: heard(said))
    return grader.grade(audio, line, target, mode, word_index)


def one(initial: int | None, final: int):
    """assemble on the single syllable 你 (or 安 when initial is None) with the given component scores."""
    ch = "安" if initial is None else "你"
    line = make_line([ch])
    p, _, ini, fin, _ = READINGS[ch]
    sound = SoundScore(initial=None if initial is None else Part(expected=ini, heard="?", score=initial),
                       final=Part(expected=fin, heard="?", score=final))
    return grader.assemble(line.syllables, line.syllables, [sound], None, None, None, heard(ch),
                           word_specs=[(0, ch, [0])], engine="whisper", trim_offset_ms=0,
                           line_index=0, target="line", mode="spoken", word_index=None)


# --- happy path: api.md's example --------------------------------------------


def test_api_example_n_heard_as_l(monkeypatch):
    r = run(monkeypatch, "我想和李一起")
    example = EXAMPLE_RESULT
    assert r.scores.model_dump() == example["scores"]
    assert r.words[3].model_dump() == example["words"][0]
    assert r.syllables[3].model_dump() == example["syllables"][0]
    assert r.heard.model_dump() == example["heard"]
    assert r.next_step.model_dump() == example["next_step"]
    assert (r.engine, r.status, r.target, r.mode) == ("whisper", "ok", "line", "spoken")
    assert [w.status for w in r.words] == ["good", "good", "good", "ok", "good"]


def test_all_good_goes_to_next_line(monkeypatch):
    r = run(monkeypatch, "我想和你一起")
    assert all(s.status == "good" and s.feedback is None for s in r.syllables)
    assert (r.scores.overall, r.next_step.type) == (100, "next_line")


# --- scoring.md rules -----------------------------------------------------------


@pytest.mark.parametrize("initial, final, score, status", [
    (100, 100, 100, "good"), (60, 100, 83, "ok"), (100, 60, 77, "ok"), (20, 100, 66, "wrong"), (60, 60, 60, "wrong"),
    (None, 100, 100, "good"), (None, 60, 60, "wrong"),
])
def test_scoring_md_syllable_table(initial, final, score, status):
    s = one(initial, final).syllables[0]
    assert (s.score, s.status) == (score, status)


@pytest.mark.parametrize("score, status", [(100, "good"), (85, "good"), (84, "ok"), (70, "ok"), (69, "wrong"), (0, "wrong")])
def test_status_thresholds(score, status):
    assert grader.status_for(score) == status


def test_round_half_up():
    assert [grader.round_half_up(x) for x in (82.5, 83.5, 97.87, 82.49)] == [83, 84, 98, 82]


def test_missing_syllable(monkeypatch):
    r = run(monkeypatch, "我想你一起")
    s = r.syllables[2]
    assert (s.status, s.score, s.feedback.code) == ("missing", 0, "MISSING")
    assert (s.initial.heard, s.initial.score, s.final.score) == (None, 0, 0)
    assert (r.words[2].status, r.words[2].score) == ("missing", 0)
    assert (r.scores.pronunciation, r.scores.completeness, r.scores.overall) == (100, 83, 95)
    assert r.next_step.type == "practice_word" and r.next_step.word_index == 2


def test_word_status_is_worst_syllable_and_score_is_mean(monkeypatch):
    r = run(monkeypatch, "我想和你一李")  # 起 heard as 李: q vs l is not a pair -> 66 wrong
    assert [s.score for s in r.syllables[4:]] == [100, 66]
    assert (r.words[4].status, r.words[4].score) == ("wrong", 83)


@pytest.mark.parametrize("said, step", [("我想", "retry_line"), ("我想和", "practice_word")])
def test_retry_line_below_50_completeness(monkeypatch, said, step):
    r = run(monkeypatch, said)
    assert r.next_step.type == step
    assert r.scores.completeness == (33 if said == "我想" else 50)


# --- word target, null rescaling, tone, timing, rhythm ----------------------------


def test_word_target_rescales_without_tone(monkeypatch):
    r = run(monkeypatch, "一李", target="word", mode="singing", word_index=4)
    assert (r.target, r.mode, r.word_index) == ("word", None, 4)
    assert [(w.index, w.text, w.syllable_indices) for w in r.words] == [(4, "一起", [0, 1])]
    assert [s.index for s in r.syllables] == [0, 1]
    assert (r.scores.pronunciation, r.scores.completeness, r.scores.tone, r.scores.overall) == (83, 100, None, 88)


def test_word_target_with_tones():
    line = make_line(["一起"])
    exp = line.syllables
    obs = sylls("一李", heard=True)
    from app.scoring.matcher import score_sounds_base
    tones = [ToneGrade(expected=4, heard=4, score=100), ToneGrade(expected=3, heard=2, score=40)]
    r = grader.assemble(exp, obs, score_sounds_base(exp, obs), None, None, tones, heard("一李"),
                        word_specs=[(0, "一起", [0, 1])], engine="whisper", trim_offset_ms=0,
                        line_index=0, target="word", mode=None, word_index=0)
    assert r.scores.tone == 70
    assert r.scores.overall == 83  # 0.5*83 + 0.2*100 + 0.3*70 = 82.5
    assert r.syllables[1].tone.heard == 2


def test_timing_adds_trim_offset_and_rhythm_counts_in_singing_mode():
    exp = LINE.syllables
    obs = sylls("我想和你一起", heard=True)
    from app.scoring.matcher import score_sounds_base
    spans = [Span(start_ms=100 * i, end_ms=100 * i + 80, confidence=0.9) for i in range(6)]
    rhythm = RhythmResult(score=80, syllables=[RhythmSyllable(offset_ms=-20, score=80)] * 6)
    common = dict(word_specs=[(w.index, w.text, w.syllable_indices) for w in LINE.words], engine="whisper+ctc",
                  trim_offset_ms=150, line_index=0, target="line", word_index=None)
    r = grader.assemble(exp, obs, score_sounds_base(exp, obs), spans, rhythm, None, heard("我想和你一起"),
                        mode="singing", **common)
    assert (r.syllables[1].timing.start_ms, r.syllables[1].timing.end_ms) == (250, 330)
    assert (r.syllables[1].timing.offset_ms, r.syllables[1].timing.score) == (-20, 80)
    assert (r.scores.rhythm, r.scores.overall) == (80, 97)  # 0.60*100 + 0.25*100 + 0.15*80
    no_rhythm = grader.assemble(exp, obs, score_sounds_base(exp, obs), spans, None, None, heard("我想和你一起"),
                                mode="singing", **common)
    assert no_rhythm.scores.overall == 100 and no_rhythm.syllables[1].timing.offset_ms is None


# --- feedback -------------------------------------------------------------------------


@pytest.mark.parametrize("expected, said, code", [
    ("安", "昂", "FINAL_AN_ANG"), ("安", "啊", "FINAL_OTHER"), ("你", "好", "INITIAL_OTHER"), ("我", "果", "INITIAL_OTHER"),
    ("知", "资", "INITIAL_ZH_Z"), ("你", "一", "INITIAL_OTHER"),
])
def test_feedback_codes(monkeypatch, expected, said, code):
    r = run(monkeypatch, said, line=make_line([expected]))
    assert r.syllables[0].feedback.code == code


def test_feedback_messages_name_the_sounds(monkeypatch):
    added = run(monkeypatch, "果", line=make_line(["我"])).syllables[0].feedback.message
    dropped = run(monkeypatch, "一", line=make_line(["你"])).syllables[0].feedback.message
    assert '"g"' in added and '"n"' in dropped


def test_tone_feedback_only_when_sounds_are_right():
    sound = SoundScore(initial=Part(expected="n", heard="n", score=100), final=Part(expected="i", heard="i", score=100))
    assert feedback.pick(sound, ToneGrade(expected=3, heard=2, score=40)).code == "TONE_3_2"
    assert feedback.pick(sound, ToneGrade(expected=3, heard=3, score=100)) is None
    assert feedback.pick(None, None).code == "MISSING"


# --- no speech and invalid input -------------------------------------------------------


def test_no_speech(monkeypatch):
    r = run(monkeypatch, "", mode="singing")
    assert (r.status, r.engine, r.mode, r.words, r.syllables, r.heard) == ("no_speech", "whisper", "singing", [], [], None)
    assert r.scores.overall is None and r.next_step.type == "retry_line"


@pytest.mark.parametrize("target, mode, word_index", [("song", "spoken", None), ("line", None, None), ("word", None, None)])
def test_bad_arguments(monkeypatch, target, mode, word_index):
    with pytest.raises(ValueError):
        run(monkeypatch, "我", target=target, mode=mode, word_index=word_index)


def test_assemble_rejects_misaligned_layers():
    exp = LINE.syllables
    with pytest.raises(ValueError):
        grader.assemble(exp, [None] * 5, [None] * 6, None, None, None, heard(""),
                        word_specs=[], engine="whisper", trim_offset_ms=0,
                        line_index=0, target="line", mode="spoken", word_index=None)
