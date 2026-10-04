"""Tests for match and score_sounds_base.

Uses hand-built syllables, so no audio or model is needed. The cases are listed
in docs/tasks/backend-api-whisper.md.

Owner: B.
"""

import re
from pathlib import Path

import pytest

from app.schemas import Syllable
from app.scoring.confusions import FINAL_PAIRS, INITIAL_PAIRS, final_partners, initial_partners
from app.scoring.matcher import match, score_sounds_base

# hanzi: (pinyin, pinyin_numeric, initial, final, tone). 我, 想 and 一 are from data-model.md;
# the rest follow the same strict-mode conventions and are written by hand.
READINGS = {
    "我": ("wǒ", "wo3", "", "uo", 3),
    "想": ("xiǎng", "xiang3", "x", "iang", 3),
    "和": ("hé", "he2", "h", "e", 2),
    "你": ("nǐ", "ni3", "n", "i", 3),
    "一": ("yì", "yi4", "", "i", 4),
    "起": ("qǐ", "qi3", "q", "i", 3),
    "李": ("lǐ", "li3", "l", "i", 3),
    "泥": ("ní", "ni2", "n", "i", 2),
    "啊": ("a", "a5", "", "a", 5),
    "好": ("hǎo", "hao3", "h", "ao", 3),
    "安": ("ān", "an1", "", "an", 1),
    "昂": ("áng", "ang2", "", "ang", 2),
    "知": ("zhī", "zhi1", "zh", "i", 1),
    "鸡": ("jī", "ji1", "j", "i", 1),
    "资": ("zī", "zi1", "z", "i", 1),
    "果": ("guǒ", "guo3", "g", "uo", 3),
    "两": ("liǎng", "liang3", "l", "iang", 3),
    "只": ("zhī", "zhi1", "zh", "i", 1),
    "老": ("lǎo", "lao3", "l", "ao", 3),
    "虎": ("hǔ", "hu3", "h", "u", 3),
    "先": ("xiān", "xian1", "x", "ian", 1),
    "香": ("xiāng", "xiang1", "x", "iang", 1),
    "关": ("guān", "guan1", "g", "uan", 1),
    "光": ("guāng", "guang1", "g", "uang", 1),
    "温": ("wēn", "wen1", "", "uen", 1),
    "翁": ("wēng", "weng1", "", "ueng", 1),
    "轻": ("qīng", "qing1", "q", "ing", 1),
    "的": ("de", "de5", "d", "e", 5),
    "地": ("dì", "di4", "d", "i", 4),   # its reading alone; as a particle it is "de"
    "得": ("dé", "de2", "d", "e", 2),
}


def sylls(text: str, heard: bool = False) -> list[Syllable]:
    """Expected syllables carry their tone; heard ones have tone None, as transcribe returns them."""
    out = []
    for ch in text:
        p, n, ini, fin, tone = READINGS[ch]
        out.append(Syllable(hanzi=ch, pinyin=p, pinyin_numeric=n, initial=ini, final=fin,
                            tone=None if heard else tone, start_ms=None, end_ms=None))
    return out


LINE = sylls("我想和你一起")


def hanzi(observed: list[Syllable | None]) -> list[str | None]:
    return [o.hanzi if o else None for o in observed]


def components(scores) -> list[tuple[int | None, int] | None]:
    return [None if s is None else (s.initial.score if s.initial else None, s.final.score) for s in scores]


# --- the spec's cases: docs/tasks/backend-api-whisper.md ---------------------


def test_exact_line_every_component_100():
    observed = match(LINE, sylls("我想和你一起", heard=True))
    assert hanzi(observed) == list("我想和你一起")
    assert components(score_sounds_base(LINE, observed)) == [
        (None, 100), (100, 100), (100, 100), (100, 100), (None, 100), (100, 100),
    ]


def test_n_heard_as_l_scores_initial_60():
    observed = match(LINE, sylls("我想和李一起", heard=True))
    assert hanzi(observed) == list("我想和李一起")
    ni = score_sounds_base(LINE, observed)[3]
    assert (ni.initial.expected, ni.initial.heard, ni.initial.score) == ("n", "l", 60)
    assert (ni.final.expected, ni.final.heard, ni.final.score) == ("i", "i", 100)


def test_same_sound_different_character_is_full_match():
    observed = match(LINE, sylls("我想和泥一起", heard=True))
    assert observed[3].hanzi == "泥"
    assert components(score_sounds_base(LINE, observed))[3] == (100, 100)


def test_missing_syllable_is_none_rest_matched():
    observed = match(LINE, sylls("我想你一起", heard=True))
    assert hanzi(observed) == ["我", "想", None, "你", "一", "起"]
    assert score_sounds_base(LINE, observed)[2] is None


def test_extra_heard_syllable_is_dropped():
    observed = match(LINE, sylls("我想和你啊一起", heard=True))
    assert hanzi(observed) == list("我想和你一起")


def test_empty_heard_gives_all_none():
    # The grader turns this into no_speech; the matcher only reports nothing matched.
    assert match(LINE, []) == [None] * 6


# --- observed syllable fields ---------------------------------------------------


def test_same_hanzi_copies_the_expected_reading():
    expected = [Syllable(hanzi="和", pinyin="hàn", pinyin_numeric="han4", initial="h", final="an", tone=4,
                         start_ms=None, end_ms=None)]
    observed = match(expected, sylls("和", heard=True))
    assert (observed[0].pinyin_numeric, observed[0].initial, observed[0].final) == ("han4", "h", "an")
    assert components(score_sounds_base(expected, observed)) == [(100, 100)]


@pytest.mark.parametrize("written", ["地", "得", "的"])
def test_de_particles_are_the_same_word(written):
    # Whisper writes 轻轻地 for a sung 轻轻的; all three particles are said "de".
    expected = sylls("轻轻的")
    observed = match(expected, sylls("轻轻" + written, heard=True))
    assert components(score_sounds_base(expected, observed)) == [(100, 100)] * 3
    assert (observed[2].hanzi, observed[2].pinyin_numeric) == (written, "de5")


def test_de_particle_rule_needs_an_expected_de():
    # 地 expected with its full reading "dì" is not the particle: a heard 的 ("de") is a different final.
    expected = sylls("地")
    observed = match(expected, sylls("的", heard=True))
    assert components(score_sounds_base(expected, observed)) == [(100, 20)]


def test_observed_tone_and_times_are_none_even_if_expected_has_them():
    expected = [s.model_copy(update={"start_ms": 0, "end_ms": 300}) for s in LINE]
    observed = match(expected, sylls("我想和你一起"))
    assert all(o.tone is None and o.start_ms is None and o.end_ms is None for o in observed)
    assert all(type(o) is Syllable for o in observed)


# --- boundaries -------------------------------------------------------------------


def test_empty_expected():
    assert match([], sylls("我", heard=True)) == []
    assert match([], []) == []
    assert score_sounds_base([], []) == []


def test_repeated_line_with_one_word_dropped():
    expected = sylls("两只老虎两只老虎")
    observed = match(expected, sylls("两只老虎老虎", heard=True))
    assert hanzi(observed) == ["两", "只", "老", "虎", None, None, "老", "虎"]


def test_skipped_word_plus_junk_is_missing_not_two_wrongs():
    # 你 skipped, 啊 added: one gap each side (3.0) beats two bad substitutions (4.0).
    observed = match(sylls("你好"), sylls("好啊", heard=True))
    assert hanzi(observed) == [None, "好"]


def test_same_character_with_another_reading_still_wins_the_alignment():
    # The lyric reads 和 as hàn; Whisper's 和 comes back as hé. It must still line up with 和, not 好.
    he_han = Syllable(hanzi="和", pinyin="hàn", pinyin_numeric="han4", initial="h", final="an", tone=4,
                      start_ms=None, end_ms=None)
    observed = match([he_han, *sylls("好")], sylls("和", heard=True))
    assert hanzi(observed) == ["和", None]


def test_result_length_always_equals_expected():
    for heard in ["", "我", "我想和你一起啊啊啊", "好好好", "起一你和想我"]:
        observed = match(LINE, sylls(heard, heard=True))
        assert len(observed) == len(LINE)
        assert len(score_sounds_base(LINE, observed)) == len(LINE)


def test_final_pair_an_ang_scores_60():
    observed = match(sylls("安"), sylls("昂", heard=True))
    assert components(score_sounds_base(sylls("安"), observed)) == [(None, 60)]


@pytest.mark.parametrize("expected, heard", [("知", "资"), ("资", "知"), ("知", "鸡"), ("鸡", "知")])
def test_initial_pairs_score_60_in_both_directions(expected, heard):
    observed = match(sylls(expected), sylls(heard, heard=True))
    assert components(score_sounds_base(sylls(expected), observed)) == [(60, 100)]


# --- mismatches and invalid input -------------------------------------------------


def test_different_syllable_substitutes_and_scores_20():
    observed = match(sylls("你"), sylls("好", heard=True))
    assert hanzi(observed) == ["好"]
    assert components(score_sounds_base(sylls("你"), observed)) == [(20, 20)]


@pytest.mark.parametrize("expected, heard, initial", [("我", "果", "g"), ("一", "你", "n")])
def test_initial_added_where_none_expected_scores_20(expected, heard, initial):
    observed = match(sylls(expected), sylls(heard, heard=True))
    score = score_sounds_base(sylls(expected), observed)[0]
    assert (score.initial.expected, score.initial.heard, score.initial.score) == ("", initial, 20)
    assert score.final.score == 100


def test_no_initial_expected_or_heard_stays_none():
    observed = match(sylls("安"), sylls("啊", heard=True))
    assert components(score_sounds_base(sylls("安"), observed)) == [(None, 20)]


def test_initial_dropped_where_one_expected_scores_20():
    observed = match(sylls("你"), sylls("一", heard=True))
    score = score_sounds_base(sylls("你"), observed)[0]
    assert (score.initial.expected, score.initial.heard, score.initial.score) == ("n", "", 20)


@pytest.mark.parametrize("expected, heard, result", [
    ("先", "香", (100, 60)), ("香", "先", (100, 60)),
    ("关", "光", (100, 60)), ("温", "翁", (None, 60)),
])
def test_nasal_pairs_in_longer_finals_score_60(expected, heard, result):
    observed = match(sylls(expected), sylls(heard, heard=True))
    assert components(score_sounds_base(sylls(expected), observed)) == [result]


def test_score_sounds_base_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        score_sounds_base(LINE, [None] * 5)


# --- confusions table ---------------------------------------------------------------


def test_table_matches_scoring_md():
    text = (Path(__file__).resolve().parents[2] / "docs" / "contracts" / "scoring.md").read_text(encoding="utf-8")
    listed = re.search(r"Commonly confused pairs: ([a-z/, ]+)\.", text)
    assert listed, "pair list not found in scoring.md"
    documented = {frozenset(p.split("/")) for p in listed.group(1).split(", ")}
    assert {frozenset(p) for p in INITIAL_PAIRS + FINAL_PAIRS} == documented
    assert len(documented) == 13


def test_partners():
    assert initial_partners("zh") == ["z", "j"]
    assert initial_partners("z") == ["zh"]
    assert final_partners("ang") == ["an"]
    assert initial_partners("b") == [] and initial_partners("") == [] and final_partners("uo") == []


def test_partners_are_symmetric():
    for a, b in INITIAL_PAIRS:
        assert b in initial_partners(a) and a in initial_partners(b)
    for a, b in FINAL_PAIRS:
        assert b in final_partners(a) and a in final_partners(b)
