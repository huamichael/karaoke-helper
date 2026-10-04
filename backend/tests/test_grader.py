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
from app.scoring.confusions import FINAL_PAIRS, INITIAL_PAIRS
from app.scoring.matcher import score_sounds_base
from tests.test_matcher import READINGS, sylls
from tests.test_schemas import EXAMPLE_RESULT

AUDIO = Audio(samples=np.zeros(16000, dtype=np.float32), sample_rate=16000, trim_offset_ms=0)


@pytest.fixture(autouse=True)
def layer_flags_off(monkeypatch):
    for name in ("ENABLE_CTC", "ENABLE_RHYTHM", "ENABLE_TONE", "TONE_REFERENCE"):
        monkeypatch.setenv(name, "0")


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


def spans_for(expected, start=0):
    return [Span(start_ms=start + 100 * i, end_ms=start + 100 * i + 80, confidence=0.9) for i in range(len(expected))]


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
    # A missing syllable counts 0 in pronunciation, so leaving words out costs as much as saying them wrong.
    assert (r.scores.pronunciation, r.scores.completeness, r.scores.overall) == (83, 83, 83)
    assert r.next_step.type == "practice_word" and r.next_step.word_index == 2


def test_missing_and_wrong_syllables_both_count_in_pronunciation(monkeypatch):
    r = run(monkeypatch, "我想你一李")  # 和 missing, 起 heard as 李 (66)
    assert [s.score for s in r.syllables] == [100, 100, 0, 100, 100, 66]
    assert (r.scores.pronunciation, r.scores.completeness, r.scores.overall) == (78, 83, 79)  # 466 / 6 = 77.7


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
    assert (r.scores.pronunciation, r.scores.completeness, r.scores.tone, r.scores.overall) == (83, 100, None, 86)  # 0.8*83 + 0.2*100


def test_word_target_with_tones():
    line = make_line(["一起"])
    exp = line.syllables
    obs = sylls("一李", heard=True)
    tones = [ToneGrade(expected=4, heard=4, score=100), ToneGrade(expected=3, heard=2, score=40)]
    r = grader.assemble(exp, obs, score_sounds_base(exp, obs), None, None, tones, heard("一李"),
                        word_specs=[(0, "一起", [0, 1])], engine="whisper", trim_offset_ms=0,
                        line_index=0, target="word", mode=None, word_index=0)
    assert r.scores.tone == 70
    assert r.scores.overall == 78  # 0.4*83 + 0.1*100 + 0.5*70 = 78.2
    assert r.syllables[1].tone.heard == 2


def test_timing_adds_trim_offset_and_rhythm_counts_in_singing_mode():
    exp = LINE.syllables
    obs = sylls("我想和你一起", heard=True)
    spans = spans_for(exp)
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


def directional_codes() -> list[tuple[str, str, str]]:
    out = []
    for prefix, pairs in (("INITIAL", INITIAL_PAIRS), ("FINAL", FINAL_PAIRS)):
        for a, b in pairs:
            out += [(f"{prefix}_{a.upper()}_{b.upper()}", a, b), (f"{prefix}_{b.upper()}_{a.upper()}", b, a)]
    return out


@pytest.mark.parametrize("code, expected, heard", directional_codes())
def test_every_confused_pair_has_a_message_naming_both_sounds(code, expected, heard):
    message = feedback.MESSAGES[code]
    assert message.startswith(f'Sounded closer to "{heard}". For "{expected}", ')


def test_catalogue_has_no_codes_outside_the_confusion_table():
    pair_codes = {code for code, _, _ in directional_codes()}
    sound_codes = {c for c in feedback.MESSAGES if c.startswith(("INITIAL_", "FINAL_"))}
    assert sound_codes == pair_codes


@pytest.mark.parametrize("expected, said, code", [("知", "资", "INITIAL_ZH_Z"), ("安", "昂", "FINAL_AN_ANG")])
def test_confused_pair_gets_its_catalogue_message(monkeypatch, expected, said, code):
    fb = run(monkeypatch, said, line=make_line([expected])).syllables[0].feedback
    assert (fb.code, fb.message) == (code, feedback.MESSAGES[code])


def tone_on_ni(tone: ToneGrade | None):
    """assemble for 你 with perfect sounds and one tone grade. The sound score is 100."""
    sound = SoundScore(initial=Part(expected="n", heard="n", score=100), final=Part(expected="i", heard="i", score=100))
    line = make_line(["你"])
    return grader.assemble(line.syllables, line.syllables, [sound], None, None, [tone], heard("你"),
                           word_specs=[(0, "你", [0])], engine="whisper", trim_offset_ms=0,
                           line_index=0, target="word", mode=None, word_index=0).syllables[0]


@pytest.mark.parametrize("tone_score, status", [
    (60, "wrong"), (69, "wrong"), (70, "ok"), (84, "ok"), (85, "ok"), (100, "ok"),
])
def test_wrong_tone_pulls_a_good_syllable_down(tone_score, status):
    s = tone_on_ni(ToneGrade(expected=3, heard=2, score=tone_score))
    assert (s.score, s.status) == (100, status)
    assert (s.feedback.code, s.feedback.message) == ("TONE_3_2", feedback.MESSAGES["TONE_3_2"])


@pytest.mark.parametrize("tone", [ToneGrade(expected=3, heard=3, score=40), ToneGrade(expected=3, heard=None, score=None), None])
def test_matching_or_unmeasured_tone_stays_good(tone):
    s = tone_on_ni(tone)
    assert (s.status, s.feedback) == ("good", None)


def ni_result(tone: ToneGrade | None = None, rhythm: RhythmSyllable | None = None, sound: SoundScore | None = None):
    """assemble for 你. Sounds are perfect unless sound is passed. Returns the whole result."""
    if sound is None:
        sound = SoundScore(initial=Part(expected="n", heard="n", score=100), final=Part(expected="i", heard="i", score=100))
    line = make_line(["你"])
    rhythm_result = None if rhythm is None else RhythmResult(score=rhythm.score, syllables=[rhythm])
    return grader.assemble(line.syllables, line.syllables, [sound], None, rhythm_result, [tone], heard("你"),
                           word_specs=[(0, "你", [0])], engine="whisper", trim_offset_ms=0,
                           line_index=0, target="word", mode=None, word_index=0)


@pytest.mark.parametrize("rhythm_score, offset_ms", [(84, -120), (70, 90), (69, 400), (0, -1)])
def test_rhythm_never_changes_colour(rhythm_score, offset_ms):
    # Chip colour is pronunciation only, in both modes; rhythm is reported in scores and timing.
    s = ni_result(rhythm=RhythmSyllable(offset_ms=offset_ms, score=rhythm_score)).syllables[0]
    assert (s.score, s.status, s.feedback) == (100, "good", None)


def test_singing_line_off_rhythm_keeps_pronunciation_colours():
    exp = LINE.syllables
    obs = sylls("我想和你一起", heard=True)
    late = RhythmResult(score=30, syllables=[RhythmSyllable(offset_ms=500, score=30)] * len(exp))
    r = grader.assemble(exp, obs, score_sounds_base(exp, obs), spans_for(exp), late, None, heard("我想和你一起"),
                        word_specs=[(w.index, w.text, w.syllable_indices) for w in LINE.words], engine="whisper+ctc",
                        trim_offset_ms=0, line_index=0, target="line", mode="singing", word_index=None)
    assert all(w.status == "good" for w in r.words) and all(s.feedback is None for s in r.syllables)
    assert r.scores.rhythm == 30 and r.scores.overall < 100
    assert r.next_step.type == "next_line"


def test_rhythm_code_starts_below_the_good_line():
    assert grader._rhythm_code(RhythmSyllable(offset_ms=-500, score=85)) is None
    assert grader._rhythm_code(RhythmSyllable(offset_ms=-500, score=84)) == "RHYTHM_EARLY"


@pytest.mark.parametrize("rhythm_score, offset_ms", [(85, -500), (100, 0), (84, 0)])
def test_rhythm_on_time_stays_good(rhythm_score, offset_ms):
    s = ni_result(rhythm=RhythmSyllable(offset_ms=offset_ms, score=rhythm_score)).syllables[0]
    assert (s.status, s.feedback) == ("good", None)


def test_sound_and_tone_messages_beat_rhythm():
    early = RhythmSyllable(offset_ms=-200, score=40)
    n_as_l = SoundScore(initial=Part(expected="n", heard="l", score=60), final=Part(expected="i", heard="i", score=100))
    sound = ni_result(rhythm=early, sound=n_as_l).syllables[0]
    assert (sound.score, sound.status, sound.feedback.code) == (83, "ok", "INITIAL_N_L")
    tone = ni_result(tone=ToneGrade(expected=3, heard=2, score=40), rhythm=early).syllables[0]
    assert (tone.status, tone.feedback.code) == ("wrong", "TONE_3_2")


def test_pronunciation_is_none_when_every_syllable_is_missing():
    line = make_line(["你", "好"])
    r = grader.assemble(line.syllables, [None, None], [None, None], None, None, None, heard("啊"),
                        word_specs=[(0, "你", [0]), (1, "好", [1])], engine="whisper", trim_offset_ms=0,
                        line_index=0, target="line", mode="spoken", word_index=None)
    assert (r.scores.pronunciation, r.scores.completeness, r.scores.overall) == (None, 0, 0)


def test_missing_syllable_beats_rhythm():
    line = make_line(["你"])
    rhythm = RhythmResult(score=40, syllables=[RhythmSyllable(offset_ms=-200, score=40)])
    s = grader.assemble(line.syllables, [None], [None], None, rhythm, [None], heard(""),
                        word_specs=[(0, "你", [0])], engine="whisper", trim_offset_ms=0,
                        line_index=0, target="word", mode=None, word_index=0).syllables[0]
    assert (s.status, s.feedback.code) == ("missing", "MISSING")


def test_sound_problem_keeps_its_colour_and_message_despite_a_wrong_tone():
    sound = SoundScore(initial=Part(expected="n", heard="l", score=60), final=Part(expected="i", heard="i", score=100))
    line = make_line(["你"])
    s = grader.assemble(line.syllables, line.syllables, [sound], None, None, [ToneGrade(expected=3, heard=2, score=40)],
                        heard("李"), word_specs=[(0, "你", [0])], engine="whisper", trim_offset_ms=0,
                        line_index=0, target="word", mode=None, word_index=0).syllables[0]
    assert (s.score, s.status, s.feedback.code) == (83, "ok", "INITIAL_N_L")


def test_tone_feedback_only_when_sounds_are_right():
    sound = SoundScore(initial=Part(expected="n", heard="n", score=100), final=Part(expected="i", heard="i", score=100))
    assert feedback.pick(sound, ToneGrade(expected=3, heard=2, score=40)).code == "TONE_3_2"
    assert feedback.pick(sound, ToneGrade(expected=3, heard=3, score=100)) is None
    assert feedback.pick(None, None).code == "MISSING"


# --- CTC layer, behind ENABLE_CTC ------------------------------------------------------


def test_singing_with_ctc_sets_engine_and_timing(monkeypatch):
    monkeypatch.setenv("ENABLE_CTC", "1")
    audio = Audio(samples=AUDIO.samples, sample_rate=16000, trim_offset_ms=150)
    monkeypatch.setattr(grader, "align", lambda a, expected: spans_for(expected))
    monkeypatch.setattr(grader, "score_sounds", lambda a, expected, spans: score_sounds_base(expected, expected))
    r = run(monkeypatch, "我想和你一起", mode="singing", audio=audio)
    assert r.engine == "whisper+ctc"
    assert (r.syllables[1].timing.start_ms, r.syllables[1].timing.end_ms) == (250, 330)
    assert all(s.timing is not None for s in r.syllables)


def test_spoken_does_not_call_ctc_when_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_CTC", "1")
    calls = []
    monkeypatch.setattr(grader, "align", lambda a, expected: calls.append("align") or spans_for(expected))
    r = run(monkeypatch, "我想和你一起", mode="spoken")
    assert calls == [] and r.engine == "whisper"
    assert all(s.timing is None for s in r.syllables)


def test_align_failure_stays_whisper(monkeypatch):
    monkeypatch.setenv("ENABLE_CTC", "1")
    monkeypatch.setattr(grader, "align", lambda *_: (_ for _ in ()).throw(RuntimeError("align down")))
    r = run(monkeypatch, "我想和你一起", mode="singing")
    assert r.engine == "whisper"
    assert r.scores.overall == 100
    assert all(s.timing is None for s in r.syllables)


def test_score_sounds_failure_keeps_spans_and_base_scores(monkeypatch):
    monkeypatch.setenv("ENABLE_CTC", "1")
    monkeypatch.setattr(grader, "align", lambda a, expected: spans_for(expected))
    monkeypatch.setattr(grader, "score_sounds", lambda *_: (_ for _ in ()).throw(RuntimeError("score down")))
    r = run(monkeypatch, "我想和李一起", mode="singing")
    assert r.engine == "whisper+ctc"
    assert r.syllables[0].timing is not None
    assert r.syllables[3].initial.score == 60


def test_word_of_two_syllables_aligns_but_does_not_rescore(monkeypatch):
    monkeypatch.setenv("ENABLE_CTC", "1")
    called = []
    monkeypatch.setattr(grader, "align", lambda a, expected: called.append("align") or spans_for(expected))
    monkeypatch.setattr(grader, "score_sounds", lambda *_: called.append("score") or [])
    r = run(monkeypatch, "一起", target="word", mode=None, word_index=4)
    assert called == ["align"]
    assert r.engine == "whisper+ctc"
    assert r.syllables[0].timing is not None


def test_one_syllable_word_does_not_call_align(monkeypatch):
    monkeypatch.setenv("ENABLE_CTC", "1")
    calls = []
    monkeypatch.setattr(grader, "align", lambda a, expected: calls.append("align") or spans_for(expected))
    r = run(monkeypatch, "我", target="word", mode=None, word_index=0)
    assert calls == [] and r.engine == "whisper"


# --- rhythm layer, behind ENABLE_RHYTHM -------------------------------------------------


def rhythm_of(score, first_offset=-120, first_score=74, n=len(LINE.syllables)):
    return RhythmResult(score=score, syllables=[RhythmSyllable(offset_ms=first_offset, score=first_score)] + [None] * (n - 1))


def singing_with_spans(monkeypatch):
    monkeypatch.setenv("ENABLE_CTC", "1")
    monkeypatch.setattr(grader, "align", lambda a, expected: spans_for(expected))
    monkeypatch.setattr(grader, "score_sounds", lambda a, expected, spans: score_sounds_base(expected, expected))


def test_singing_with_rhythm_fills_score_offsets_and_weights(monkeypatch):
    singing_with_spans(monkeypatch)
    monkeypatch.setenv("ENABLE_RHYTHM", "1")
    calls = []
    monkeypatch.setattr(grader, "score_rhythm", lambda ref, spans: calls.append((ref, spans)) or rhythm_of(40))
    r = run(monkeypatch, "我想和你一起", mode="singing")
    assert calls == [(LINE.syllables, spans_for(LINE.syllables))]
    assert r.scores.rhythm == 40
    assert r.scores.overall == 91  # 0.60*100 + 0.25*100 + 0.15*40
    assert (r.syllables[0].timing.offset_ms, r.syllables[0].timing.score) == (-120, 74)
    assert (r.syllables[1].timing.offset_ms, r.syllables[1].timing.score) == (None, None)
    assert r.engine == "whisper+ctc"


def test_rhythm_none_drops_out_of_overall(monkeypatch, caplog):
    singing_with_spans(monkeypatch)
    monkeypatch.setattr(grader, "score_sounds", lambda a, e, s: score_sounds_base(e, sylls("我想和李一起", heard=True)))
    monkeypatch.setenv("ENABLE_RHYTHM", "1")
    monkeypatch.setattr(grader, "score_rhythm", lambda ref, spans: None)
    r = run(monkeypatch, "我想和李一起", mode="singing")
    assert caplog.records == []
    assert r.scores.rhythm is None
    assert r.scores.overall == EXAMPLE_RESULT["scores"]["overall"]  # same line, spoken weights
    assert all(s.timing.offset_ms is None for s in r.syllables)


@pytest.mark.parametrize("ctc, rhythm, mode", [("0", "1", "singing"), ("1", "0", "singing"), ("1", "1", "spoken")])
def test_rhythm_not_called_without_spans_switch_or_singing(monkeypatch, ctc, rhythm, mode):
    monkeypatch.setenv("ENABLE_CTC", ctc)
    monkeypatch.setenv("ENABLE_RHYTHM", rhythm)
    monkeypatch.setattr(grader, "align", lambda a, expected: spans_for(expected))
    monkeypatch.setattr(grader, "score_sounds", lambda a, expected, spans: score_sounds_base(expected, expected))
    calls = []
    monkeypatch.setattr(grader, "score_rhythm", lambda *a: calls.append(a) or rhythm_of(40))
    r = run(monkeypatch, "我想和你一起", mode=mode)
    assert calls == [] and r.scores.rhythm is None


def test_rhythm_not_called_when_align_fails(monkeypatch):
    monkeypatch.setenv("ENABLE_CTC", "1")
    monkeypatch.setenv("ENABLE_RHYTHM", "1")
    monkeypatch.setattr(grader, "align", lambda *_: (_ for _ in ()).throw(RuntimeError("align down")))
    calls = []
    monkeypatch.setattr(grader, "score_rhythm", lambda *a: calls.append(a) or rhythm_of(40))
    r = run(monkeypatch, "我想和你一起", mode="singing")
    assert calls == []
    assert (r.engine, r.scores.rhythm, r.scores.overall) == ("whisper", None, 100)


def test_rhythm_failure_keeps_ctc_result(monkeypatch):
    singing_with_spans(monkeypatch)
    monkeypatch.setenv("ENABLE_RHYTHM", "1")
    monkeypatch.setattr(grader, "score_rhythm", lambda *_: (_ for _ in ()).throw(RuntimeError("rhythm down")))
    r = run(monkeypatch, "我想和你一起", mode="singing")
    assert (r.engine, r.scores.rhythm, r.scores.overall) == ("whisper+ctc", None, 100)
    assert all(s.timing is not None and s.timing.offset_ms is None for s in r.syllables)


# --- tone layer, behind ENABLE_TONE -----------------------------------------------------


def fake_tones(grades):
    calls = []
    return calls, lambda audio, expected, spans: calls.append((audio, list(expected), spans)) or grades


def test_one_syllable_word_tone_uses_whole_recording(monkeypatch):
    monkeypatch.setenv("ENABLE_TONE", "1")
    grade3 = ToneGrade(expected=3, heard=3, score=90)
    calls, fake = fake_tones([grade3])
    monkeypatch.setattr(grader, "score_tones", fake)
    r = run(monkeypatch, "我", target="word", mode=None, word_index=0)
    assert calls == [(AUDIO, [LINE.syllables[0]], None)]
    assert (r.scores.tone, r.syllables[0].tone) == (90, grade3)
    assert r.scores.overall == 95  # 0.40*100 + 0.10*100 + 0.50*90


def test_two_syllable_word_tone_uses_ctc_spans_and_skips_unscored(monkeypatch):
    monkeypatch.setenv("ENABLE_CTC", "1")
    monkeypatch.setenv("ENABLE_TONE", "1")
    monkeypatch.setattr(grader, "align", lambda a, expected: spans_for(expected))
    calls, fake = fake_tones([ToneGrade(expected=4, heard=None, score=None), ToneGrade(expected=3, heard=2, score=40)])
    monkeypatch.setattr(grader, "score_tones", fake)
    r = run(monkeypatch, "一起", target="word", mode=None, word_index=4)
    assert [c[2] for c in calls] == [spans_for(LINE.syllables[4:6])]
    assert r.scores.tone == 40
    assert r.scores.overall == 70  # 0.40*100 + 0.10*100 + 0.50*40
    assert r.engine == "whisper+ctc"


@pytest.mark.parametrize("ctc, tone, target, mode, word_index", [
    ("0", "1", "word", None, 4),         # two syllables, no spans: contract forbids spans=None
    ("1", "0", "word", None, 0),         # switch off
    ("1", "1", "line", "singing", None), # lines never get tone
    ("1", "1", "line", "spoken", None),
])
def test_tone_not_called(monkeypatch, ctc, tone, target, mode, word_index):
    monkeypatch.setenv("ENABLE_CTC", ctc)
    monkeypatch.setenv("ENABLE_TONE", tone)
    monkeypatch.setattr(grader, "align", lambda a, expected: spans_for(expected))
    monkeypatch.setattr(grader, "score_sounds", lambda a, expected, spans: score_sounds_base(expected, expected))
    calls, fake = fake_tones([])
    monkeypatch.setattr(grader, "score_tones", fake)
    said = "我想和你一起" if target == "line" else ("一起" if word_index == 4 else "我")
    r = run(monkeypatch, said, target=target, mode=mode, word_index=word_index)
    assert calls == [] and r.scores.tone is None


def test_tone_not_called_when_align_fails_on_two_syllables(monkeypatch):
    monkeypatch.setenv("ENABLE_CTC", "1")
    monkeypatch.setenv("ENABLE_TONE", "1")
    monkeypatch.setattr(grader, "align", lambda *_: (_ for _ in ()).throw(RuntimeError("align down")))
    calls, fake = fake_tones([])
    monkeypatch.setattr(grader, "score_tones", fake)
    r = run(monkeypatch, "一起", target="word", mode=None, word_index=4)
    assert calls == []
    assert (r.engine, r.scores.tone, r.scores.overall) == ("whisper", None, 100)


def test_real_score_tones_runs_through_grade_on_silence(monkeypatch):
    monkeypatch.setenv("ENABLE_TONE", "1")
    r = run(monkeypatch, "我", target="word", mode=None, word_index=0)
    assert r.syllables[0].tone == ToneGrade(expected=3, heard=None, score=None)
    assert (r.scores.tone, r.scores.overall) == (None, 100)


def test_tone_failure_keeps_whisper_result(monkeypatch):
    monkeypatch.setenv("ENABLE_TONE", "1")
    monkeypatch.setattr(grader, "score_tones", lambda *_: (_ for _ in ()).throw(RuntimeError("no pitch")))
    r = run(monkeypatch, "我", target="word", mode=None, word_index=0)
    assert (r.status, r.scores.tone, r.syllables[0].tone, r.scores.overall) == ("ok", None, None, 100)


# --- a layer returning the wrong number of entries is dropped -------------------------


def test_short_align_drops_ctc(monkeypatch):
    singing_with_spans(monkeypatch)
    monkeypatch.setattr(grader, "align", lambda a, expected: spans_for(expected)[:-1])
    r = run(monkeypatch, "我想和你一起", mode="singing")
    assert (r.engine, r.scores.overall) == ("whisper", 100)
    assert all(s.timing is None for s in r.syllables)


def test_short_score_sounds_keeps_base_scores(monkeypatch):
    singing_with_spans(monkeypatch)
    monkeypatch.setattr(grader, "score_sounds", lambda a, e, s: score_sounds_base(e, e)[:-1])
    r = run(monkeypatch, "我想和李一起", mode="singing")
    assert r.engine == "whisper+ctc"
    assert r.syllables[3].initial.score == 60


def test_short_rhythm_is_dropped(monkeypatch):
    singing_with_spans(monkeypatch)
    monkeypatch.setenv("ENABLE_RHYTHM", "1")
    monkeypatch.setattr(grader, "score_rhythm", lambda ref, spans: rhythm_of(40, n=len(ref) - 1))
    r = run(monkeypatch, "我想和你一起", mode="singing")
    assert (r.engine, r.scores.rhythm, r.scores.overall) == ("whisper+ctc", None, 100)


def test_long_tones_are_dropped(monkeypatch):
    monkeypatch.setenv("ENABLE_TONE", "1")
    extra = [ToneGrade(expected=3, heard=3, score=10)] * 2
    monkeypatch.setattr(grader, "score_tones", lambda *_: extra)
    r = run(monkeypatch, "我", target="word", mode=None, word_index=0)
    assert (r.scores.tone, r.syllables[0].tone, r.scores.overall) == (None, None, 100)


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


# --- experiments: TONE_REFERENCE --------------------------------------------------


def test_tone_reference_passes_each_syllables_reference_contour(monkeypatch):
    monkeypatch.setenv("ENABLE_TONE", "1")
    monkeypatch.setenv("TONE_REFERENCE", "1")
    reference = [np.arange(5.0)]
    monkeypatch.setattr(grader, "_reference_contours", lambda line, expected: reference)
    calls = []
    monkeypatch.setattr(grader, "score_tones_with_references",
                        lambda audio, expected, spans, refs: calls.append(refs) or [ToneGrade(expected=3, heard=3, score=90)])
    monkeypatch.setattr(grader, "score_tones", lambda *a: pytest.fail("the plain tone check ran"))
    r = run(monkeypatch, "我", target="word", mode=None, word_index=0)
    assert calls == [reference] and r.scores.tone == 90


def test_tone_reference_off_uses_the_plain_tone_check(monkeypatch):
    monkeypatch.setenv("ENABLE_TONE", "1")
    calls = []
    monkeypatch.setattr(grader, "score_tones", lambda audio, expected, spans: calls.append(1) or [ToneGrade(expected=3, heard=3, score=90)])
    monkeypatch.setattr(grader, "score_tones_with_references", lambda *a: calls.append(2) or [None])
    run(monkeypatch, "我", target="word", mode=None, word_index=0)
    assert calls == [1]


def test_reference_contours_come_from_the_word_clip():
    from app import songs
    line = songs.get_line(songs.get_song("jasmine-flower"), 0)
    no_clip = line.model_copy(update={"words": [w.model_copy(update={"audio_url": None}) for w in line.words]})
    expected = songs.word_syllables(line, 0)  # 好, a one-syllable word
    [contour] = grader._reference_contours(line, expected)
    assert contour is not None and contour.shape == (5,)
    assert grader._reference_contours(no_clip, expected) == [None]


def test_reference_contours_give_each_syllable_its_own_part_of_the_clip(monkeypatch):
    from app import songs
    line = songs.get_line(songs.get_song("jasmine-flower"), 0)  # 好 / 一朵 / 美麗 / 的 / 茉莉花
    monkeypatch.setattr(grader, "_CLIP_CONTOURS", {})
    monkeypatch.setattr(grader, "align", lambda clip, sylls: [None] * len(sylls))
    monkeypatch.setattr(grader, "syllable_contours",
                        lambda clip, sylls, spans: [np.full(5, float(k)) for k in range(len(sylls))])
    contours = grader._reference_contours(line, line.syllables)
    assert [float(c[0]) for c in contours] == [0, 0, 1, 0, 1, 0, 0, 1, 2]
