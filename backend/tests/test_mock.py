"""Tests for the mock grader in app/scoring/mock.py.

Expected statuses and numbers are worked out by hand from the cycle
good, good, ok, good, wrong, good, missing, shifted by the line index.

Owner: B.
"""

import pytest

from app import songs
from app.schemas import AttemptResult, Line, LyricSyllable, Word
from app.scoring.mock import grade_mock
from app.songs import NotFound

AUDIO = b"\0" * 4096
DEMO = songs.get_song("demo")


def run(line: Line, target="line", mode="spoken", word_index=None, data=AUDIO) -> AttemptResult:
    return grade_mock(data, "demo", line, target, mode, word_index, "att_test")


def make_line(index: int, sylls: list[tuple[str, str, str, str, str, int]]) -> Line:
    """One word per syllable. Each tuple: hanzi, pinyin, pinyin_numeric, initial, final, tone."""
    return Line(
        index=index, start_ms=0, end_ms=1000, text="".join(s[0] for s in sylls), translation=None,
        syllables=[
            LyricSyllable(index=i, word_index=i, hanzi=h, pinyin=p, pinyin_numeric=n, initial=ini, final=fin,
                          tone=t, start_ms=None, end_ms=None)
            for i, (h, p, n, ini, fin, t) in enumerate(sylls)
        ],
        words=[Word(index=i, text=s[0], syllable_indices=[i], gloss=None, audio_url=None)
               for i, s in enumerate(sylls)],
    )


WO = ("我", "wǒ", "wo3", "", "uo", 3)
NI = ("你", "nǐ", "ni3", "n", "i", 3)


# --- happy path ---------------------------------------------------------------


def test_line_0_statuses_and_every_word_colour():
    r = run(DEMO.lines[0])
    assert [s.status for s in r.syllables] == ["good", "good", "ok", "good", "wrong", "good", "missing", "good"]
    assert [(w.text, w.status, w.score) for w in r.words] == [
        ("两只", "good", 100), ("老虎", "ok", 90), ("两只", "wrong", 70), ("老虎", "missing", 50),
    ]
    assert (r.scores.pronunciation, r.scores.completeness, r.scores.overall) == (89, 88, 88)
    assert (r.scores.rhythm, r.scores.tone, r.scores.melody) == (None, None, None)
    assert r.next_step.type == "practice_word"
    assert r.next_step.word_index == 3
    assert r.heard is not None and r.heard.hanzi == "两只老虎两只虎"


def test_line_1_is_shifted_by_line_index():
    r = run(DEMO.lines[1])
    assert [s.status for s in r.syllables] == ["good", "ok", "good", "wrong", "good", "missing"]
    assert [(w.status, w.score) for w in r.words] == [("ok", 93), ("missing", 47)]
    assert r.next_step.type == "practice_word" and r.next_step.word_index == 1


def test_result_fields_for_a_line():
    r = run(DEMO.lines[0], mode="singing")
    assert (r.attempt_id, r.song_id, r.line_index, r.word_index) == ("att_test", "demo", 0, None)
    assert (r.target, r.mode, r.status, r.engine) == ("line", "singing", "ok", "mock")
    assert [s.index for s in r.syllables] == list(range(8))
    assert [s.hanzi for s in r.syllables] == list("两只老虎两只老虎")
    assert [w.syllable_indices for w in r.words] == [[0, 1], [2, 3], [4, 5], [6, 7]]
    assert all(s.timing is None and s.tone is None for s in r.syllables)


def test_part_details_match_status():
    by_status = {s.status: s for s in run(DEMO.lines[0]).syllables}
    good, ok, wrong, missing = (by_status[k] for k in ("good", "ok", "wrong", "missing"))
    assert good.feedback is None and good.initial.heard == good.initial.expected
    assert ok.initial.score == 80 and ok.initial.heard == "?" and ok.final.score == 100
    assert ok.feedback.code == "INITIAL_OTHER"
    assert wrong.initial.score == 40
    assert missing.feedback.code == "MISSING"
    assert (missing.initial.heard, missing.initial.score, missing.final.score) == (None, 0, 0)


def test_word_target():
    r = run(DEMO.lines[0], target="word", mode="singing", word_index=3)
    assert (r.target, r.mode, r.word_index) == ("word", None, 3)
    assert [(s.index, s.hanzi, s.status) for s in r.syllables] == [(0, "老", "missing"), (1, "虎", "good")]
    assert [(w.index, w.text, w.status, w.syllable_indices) for w in r.words] == [(3, "老虎", "missing", [0, 1])]
    assert (r.scores.pronunciation, r.scores.completeness, r.scores.overall) == (100, 50, 75)


def test_good_word_suggests_retrying_the_line():
    r = run(DEMO.lines[0], target="word", word_index=0)
    assert r.words[0].status == "good"
    assert r.next_step.type == "retry_line"


def test_json_round_trip_and_determinism():
    r = run(DEMO.lines[1])
    assert AttemptResult.model_validate_json(r.model_dump_json()) == r
    assert run(DEMO.lines[1]) == r


# --- boundaries -----------------------------------------------------------------


@pytest.mark.parametrize("size, status", [(0, "no_speech"), (2047, "no_speech"), (2048, "ok")])
def test_no_speech_threshold(size, status):
    r = run(DEMO.lines[0], data=b"\0" * size)
    assert r.status == status
    if status == "no_speech":
        assert (r.words, r.syllables, r.heard) == ([], [], None)
        assert r.scores.overall is None and r.next_step.type == "retry_line"


def test_all_missing_word_has_null_pronunciation():
    line = make_line(6, [NI])
    r = run(line, target="word", word_index=0)
    assert r.syllables[0].status == "missing"
    assert (r.scores.pronunciation, r.scores.completeness, r.scores.overall) == (None, 0, 0)
    assert r.heard is None


def test_syllable_without_initial_has_null_initial():
    r = run(make_line(0, [WO, NI]))
    assert r.syllables[0].initial is None
    assert r.syllables[0].final.expected == "uo"
    assert r.syllables[1].initial.expected == "n"


def test_ok_without_initial_marks_the_final():
    r = run(make_line(2, [WO]))
    s = r.syllables[0]
    assert (s.status, s.initial, s.final.score, s.feedback.code) == ("ok", None, 80, "FINAL_OTHER")


# --- failures -------------------------------------------------------------------


@pytest.mark.parametrize("target, mode, word_index", [
    ("song", "spoken", None),
    ("line", None, None),
    ("line", "rap", None),
    ("word", None, None),
])
def test_bad_arguments_raise_value_error(target, mode, word_index):
    with pytest.raises(ValueError):
        run(DEMO.lines[0], target=target, mode=mode, word_index=word_index)


@pytest.mark.parametrize("word_index", [4, -1])
def test_word_index_out_of_range(word_index):
    with pytest.raises(NotFound) as e:
        run(DEMO.lines[0], target="word", word_index=word_index)
    assert e.value.code == "word_not_found"
