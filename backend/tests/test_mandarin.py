"""Tests for to_syllables, segment_words and sandhi_tones.

The expected values are the examples table in docs/contracts/data-model.md,
section 2.

Owner: D.
"""

from pathlib import Path

import pytest
import yaml

from app.mandarin import _HANZI_RUN, sandhi_tones, segment_words, to_syllables

SONGS = Path(__file__).resolve().parents[2] / "data" / "songs"


def fields(syllable):
    return (syllable.pinyin, syllable.pinyin_numeric, syllable.initial, syllable.final, syllable.tone)


# docs/contracts/data-model.md, section 2. Each case is (text, index of the syllable, expected).
@pytest.mark.parametrize(
    ("text", "index", "expected"),
    [
        ("我", 0, ("wǒ", "wo3", "", "uo", 3)),
        ("想", 0, ("xiǎng", "xiang3", "x", "iang", 3)),
        ("一起", 0, ("yì", "yi4", "", "i", 4)),
        ("就", 0, ("jiù", "jiu4", "j", "iou", 4)),
        ("会", 0, ("huì", "hui4", "h", "uei", 4)),
        ("准", 0, ("zhǔn", "zhun3", "zh", "uen", 3)),
        ("女", 0, ("nǚ", "nv3", "n", "v", 3)),
        ("月", 0, ("yuè", "yue4", "", "ve", 4)),
        ("我的", 1, ("de", "de5", "d", "e", 5)),
    ],
)
def test_contract_examples(text, index, expected):
    assert fields(to_syllables(text)[index]) == expected


def test_one_syllable_per_hanzi_in_order():
    syllables = to_syllables("我想和你一起")
    assert [s.hanzi for s in syllables] == list("我想和你一起")
    assert [s.pinyin_numeric for s in syllables] == ["wo3", "xiang3", "he2", "ni3", "yi4", "qi3"]


def test_non_hanzi_dropped():
    syllables = to_syllables("我love你，好!")
    assert [s.hanzi for s in syllables] == ["我", "你", "好"]


def test_spaces_between_phrases_dropped():
    assert len(to_syllables("我的情也真 我的愛也真")) == 10


def test_empty_text():
    assert to_syllables("") == []
    assert to_syllables("  ...  ") == []


def test_traditional_and_simplified_read_the_same():
    assert fields(to_syllables("愛")[0]) == fields(to_syllables("爱")[0])
    assert fields(to_syllables("麗")[0]) == fields(to_syllables("丽")[0])


def test_times_are_empty():
    syllable = to_syllables("你")[0]
    assert syllable.start_ms is None and syllable.end_ms is None


def test_override_replaces_reading():
    syllables = to_syllables("你的眼睛", {1: "di4"})
    assert fields(syllables[1]) == ("dì", "di4", "d", "i", 4)
    assert syllables[0].pinyin_numeric == "ni3"


def test_override_position_counts_spaces():
    # Position 7 is the second 的: the space at position 5 is counted.
    syllables = to_syllables("我的情也真 我的愛也真", {7: "di4"})
    assert syllables[1].pinyin_numeric == "de5"
    assert syllables[6].pinyin_numeric == "di4"


def test_override_accepts_u_umlaut():
    assert fields(to_syllables("女", {0: "nü3"})[0]) == ("nǚ", "nv3", "n", "v", 3)


@pytest.mark.parametrize("overrides", [{5: "de5"}, {99: "de5"}, {-1: "de5"}])
def test_override_must_point_at_hanzi(overrides):
    with pytest.raises(ValueError, match="not a Hanzi"):
        to_syllables("我的情也真 我的愛也真", overrides)


@pytest.mark.parametrize("reading", ["di", "dì", "di6", "4di", ""])
def test_override_must_be_valid_reading(reading):
    with pytest.raises(ValueError, match="no valid reading"):
        to_syllables("的", {0: reading})


def song_lines():
    for path in sorted(SONGS.glob("*/lyrics.yaml")):
        song = yaml.safe_load(path.read_text(encoding="utf-8"))
        for line in song["lines"]:
            if line["text"].strip():
                yield pytest.param(line["text"], id=f"{path.parent.name}:{line['start_ms']}")


@pytest.mark.parametrize("text", list(song_lines()))
def test_every_song_line_converts(text):
    syllables = to_syllables(text)
    assert [s.hanzi for s in syllables] == [c for c in text if _HANZI_RUN.fullmatch(c)]
    for s in syllables:
        assert s.pinyin and s.final and s.tone in (1, 2, 3, 4, 5)
        assert s.pinyin_numeric.endswith(str(s.tone))


# segment_words


def test_segment_words_simplified():
    assert segment_words("我想和你一起") == ["我", "想", "和", "你", "一起"]


def test_segment_words_traditional_uses_simplified_dictionary():
    # Segmented directly, jieba splits Traditional text badly (你問 / 我 / 愛 ...).
    assert segment_words("已經打動我的心") == ["已經", "打動", "我", "的", "心"]


def test_segment_words_never_crosses_spaces_or_punctuation():
    assert segment_words("天地 一片，苍茫") == ["天地", "一片", "苍茫"]


def test_segment_words_joins_back_to_the_hanzi():
    for text in ["你問我愛你有多深", "讓我來將你摘下 送給別人家", "雪花飘飘 北风萧萧"]:
        assert "".join(segment_words(text)) == "".join(text.split())


# sandhi_tones


def tones(text):
    return sandhi_tones(to_syllables(text))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("你好", [2, 3]),             # third tone before third tone
        ("我也想", [2, 2, 3]),        # a run of third tones: all but the last change
        ("我的", [3, None]),          # the neutral tone is not scored
        ("一片", [2, 4]),             # 一 before a fourth tone
        ("一翦", [4, 3]),             # 一 before another tone
        ("一個", [2, 4]),
        ("統一", [3, 1]),             # 一 at the end keeps its first tone
        ("第一", [4, 1]),             # ordinal 一 keeps its first tone
        ("想一想", [3, None, 3]),     # 一 between copies of the same character is neutral
        ("不變", [2, 4]),             # 不 before a fourth tone
        ("不移", [4, 2]),
        ("好不好", [3, None, 3]),
    ],
)
def test_sandhi_tones(text, expected):
    assert tones(text) == expected
