"""Tests for the song pipeline's build_song step.

Covers turning a song's phrase readings into per-line overrides, including the
readings in the demo songs' lyrics.yaml files.

Owner: D.
"""

from pathlib import Path

import pytest
import yaml

from app.mandarin import to_syllables
from pipeline.build_song import build_song, reading_overrides, word_splits, write_song

SONGS = Path(__file__).resolve().parents[2] / "data" / "songs"


def test_phrase_fixed_wherever_it_appears():
    texts = ["冷冷冰雪不能掩没", "真情像草原广阔", "掩没 掩没"]
    assert reading_overrides(texts, {"掩没": "yan3 mo4"}) == [
        {6: "yan3", 7: "mo4"},
        {},
        {0: "yan3", 1: "mo4", 3: "yan3", 4: "mo4"},
    ]


def test_overrides_feed_to_syllables():
    texts = ["此情 长留 心间"]
    [overrides] = reading_overrides(texts, {"长留": "chang2 liu2"})
    assert [s.pinyin for s in to_syllables(texts[0], overrides)] == ["cǐ", "qíng", "cháng", "liú", "xīn", "jiān"]


def test_no_readings():
    assert reading_overrides(["你好"], {}) == [{}]


def test_wrong_syllable_count():
    with pytest.raises(ValueError, match="has 1 syllables, expected 2"):
        reading_overrides(["此情长留"], {"长留": "chang2"})


def test_phrase_must_be_hanzi():
    with pytest.raises(ValueError, match="only Hanzi"):
        reading_overrides(["此情 长留"], {"情 长": "qing2 chang2"})


def test_unmatched_phrase_is_reported():
    # Traditional 長 does not match a Simplified lyric.
    with pytest.raises(ValueError, match="matches no line"):
        reading_overrides(["此情长留心间"], {"長留": "chang2 liu2"})


def test_conflicting_phrases():
    with pytest.raises(ValueError, match="conflicting readings"):
        reading_overrides(["此情长留"], {"长留": "chang2 liu2", "长": "zhang3"})


def test_agreeing_phrases_allowed():
    assert reading_overrides(["此情长留"], {"长留": "chang2 liu2", "长": "chang2"}) == [{2: "chang2", 3: "liu2"}]


@pytest.mark.parametrize("path", sorted(SONGS.glob("*/lyrics.yaml")), ids=lambda p: p.parent.name)
def test_song_readings_apply(path):
    song = yaml.safe_load(path.read_text(encoding="utf-8"))
    texts = [line["text"] for line in song["lines"]]
    for text, overrides in zip(texts, reading_overrides(texts, song.get("readings") or {})):
        to_syllables(text, overrides)


def test_yi_jian_mei_corrections():
    path = SONGS / "yi-jian-mei" / "lyrics.yaml"
    if not path.exists():
        pytest.skip("yi-jian-mei is not in data/songs")
    song = yaml.safe_load(path.read_text(encoding="utf-8"))
    texts = [line["text"] for line in song["lines"]]
    pinyin = {
        text: " ".join(s.pinyin for s in to_syllables(text, overrides))
        for text, overrides in zip(texts, reading_overrides(texts, song["readings"]))
    }
    assert pinyin["冷冷冰雪不能掩没"] == "lěng lěng bīng xuě bù néng yǎn mò"
    assert pinyin["此情 长留 心间"] == "cǐ qíng cháng liú xīn jiān"


# word_splits


def test_word_fix_applies_wherever_it_appears():
    texts = ["又香又白人人誇", "人人誇"]
    assert word_splits(texts, {"又香又白人人誇": "又 香 又 白 人人 誇"}) == [
        ["又", "香", "又", "白", "人人", "誇"],
        ["人人", "誇"],
    ]


def test_long_words_split_into_pairs():
    assert word_splits(["爱我所爱 无怨无悔"], {}) == [["爱我", "所爱", "无怨", "无悔"]]


def test_word_fix_keeps_long_word_whole():
    assert word_splits(["爱我所爱"], {"爱我所爱": "爱我所爱"}) == [["爱我所爱"]]


@pytest.mark.parametrize(
    ("fixes", "message"),
    [
        ({"长留": "长 流"}, "does not join back"),
        ({"长 留": "长 留"}, "only Hanzi"),
        ({"心间": "心间"}, "matches no line"),
    ],
)
def test_bad_word_fixes(fixes, message):
    with pytest.raises(ValueError, match=message):
        word_splits(["此情长留"], fixes)


# build_song


def write_song_folder(tmp_path, lyrics):
    folder = tmp_path / "test-song"
    folder.mkdir()
    (folder / "lyrics.yaml").write_text(yaml.safe_dump(lyrics, allow_unicode=True), encoding="utf-8")
    return folder


LYRICS = {
    "metadata": {"title": "Test", "artist": "Nobody"},
    "readings": {"长留": "chang2 liu2"},
    "words": {"心间": "心间"},
    "translations": {"此情 长留 心间": "This love stays in my heart"},
    "glosses": {"长留": "to stay forever"},
    "lines": [
        {"text": "", "start_ms": 0, "end_ms": 1000},
        {"text": "此情 长留 心间", "start_ms": 1000, "end_ms": 5000},
        {"text": "我想和你一起", "start_ms": 5000, "end_ms": 9000},
        {"text": "", "start_ms": 9000},
    ],
}


def test_build_song(tmp_path):
    song = build_song(write_song_folder(tmp_path, LYRICS), make_clips=False)
    assert song.id == "test-song" and song.line_count == 2
    assert song.audio_url == "/media/songs/test-song/audio.mp3"
    first, second = song.lines
    assert (first.index, first.start_ms, first.end_ms) == (0, 1000, 5000)
    assert first.translation == "This love stays in my heart" and second.translation is None
    assert [w.text for w in first.words] == ["此情", "长留", "心间"]
    assert first.words[1].gloss == "to stay forever" and first.words[1].syllable_indices == [2, 3]
    assert [s.pinyin for s in first.syllables] == ["cǐ", "qíng", "cháng", "liú", "xīn", "jiān"]
    assert [(s.index, s.word_index) for s in first.syllables] == [(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (5, 2)]
    assert all(s.start_ms is None for s in first.syllables)
    assert all(w.audio_url is None for w in first.words)  # no clips generated


def test_build_song_links_existing_clips(tmp_path):
    folder = write_song_folder(tmp_path, LYRICS)
    (folder / "words").mkdir()
    (folder / "words" / "chang2-liu2.mp3").write_bytes(b"")
    song = build_song(folder, make_clips=False)
    assert song.lines[0].words[1].audio_url == "/media/songs/test-song/words/chang2-liu2.mp3"


def test_build_song_keeps_aligned_times(tmp_path):
    folder = write_song_folder(tmp_path, LYRICS)
    song = build_song(folder, make_clips=False)
    for i, syllable in enumerate(song.lines[0].syllables):
        syllable.start_ms, syllable.end_ms = 1000 + i * 100, 1090 + i * 100
    write_song(folder, song)

    rebuilt = build_song(folder, make_clips=False)
    assert [s.start_ms for s in rebuilt.lines[0].syllables] == [1000, 1100, 1200, 1300, 1400, 1500]
    assert rebuilt.lines[1].syllables[0].start_ms is None


def test_build_song_drops_times_when_a_line_changes(tmp_path):
    folder = write_song_folder(tmp_path, LYRICS)
    song = build_song(folder, make_clips=False)
    song.lines[0].syllables[0].start_ms = 1000
    write_song(folder, song)

    changed = {**LYRICS, "readings": {"长留": "zhang3 liu2"}}  # a different reading: re-align
    (folder / "lyrics.yaml").write_text(yaml.safe_dump(changed, allow_unicode=True), encoding="utf-8")
    assert build_song(folder, make_clips=False).lines[0].syllables[0].start_ms is None


def test_build_song_keeps_times_when_a_line_moves(tmp_path):
    folder = write_song_folder(tmp_path, LYRICS)
    song = build_song(folder, make_clips=False)
    song.lines[0].syllables[0].start_ms, song.lines[0].syllables[0].end_ms = 1000, 1200
    write_song(folder, song)

    moved = {**LYRICS, "lines": [{**LYRICS["lines"][0], "end_ms": 850},
                                 {**LYRICS["lines"][1], "start_ms": 850}, LYRICS["lines"][2]]}
    (folder / "lyrics.yaml").write_text(yaml.safe_dump(moved, allow_unicode=True), encoding="utf-8")
    line = build_song(folder, make_clips=False).lines[0]
    assert (line.start_ms, line.syllables[0].start_ms) == (850, 1000)


def test_build_song_matches_repeated_lines_by_occurrence(tmp_path):
    lyrics = {**LYRICS, "lines": [
        {"text": "我想和你一起", "start_ms": 0, "end_ms": 1000},
        {"text": "我想和你一起", "start_ms": 1000, "end_ms": 2000},
    ]}
    folder = write_song_folder(tmp_path, {k: v for k, v in lyrics.items() if k not in ("readings", "translations", "glosses", "words")})
    song = build_song(folder, make_clips=False)
    song.lines[0].syllables[0].start_ms, song.lines[0].syllables[0].end_ms = 100, 200
    song.lines[1].syllables[0].start_ms, song.lines[1].syllables[0].end_ms = 1100, 1200
    write_song(folder, song)
    rebuilt = build_song(folder, make_clips=False)
    assert [l.syllables[0].start_ms for l in rebuilt.lines] == [100, 1100]


def test_build_song_keeps_times_when_a_line_is_trimmed(tmp_path):
    folder = write_song_folder(tmp_path, LYRICS)
    song = build_song(folder, make_clips=False)
    for i, syllable in enumerate(song.lines[0].syllables):  # line 0 runs 1000-5000
        syllable.start_ms, syllable.end_ms = 1000 + i * 500, 1300 + i * 500
    write_song(folder, song)

    trimmed = {**LYRICS, "lines": [{**LYRICS["lines"][1], "end_ms": 3200}, LYRICS["lines"][2]]}
    (folder / "lyrics.yaml").write_text(yaml.safe_dump(trimmed, allow_unicode=True), encoding="utf-8")
    line = build_song(folder, make_clips=False).lines[0]
    assert line.end_ms == 3200
    assert [s.start_ms for s in line.syllables] == [1000, 1500, 2000, 2500, 3000, None]
    assert line.syllables[4].end_ms == 3200  # clipped to the new end


@pytest.mark.parametrize(
    ("lines", "message"),
    [
        ([{"text": "你好", "start_ms": 1000}], "start_ms < end_ms"),
        ([{"text": "你好", "start_ms": 2000, "end_ms": 1000}], "start_ms < end_ms"),
        ([{"text": "你好", "start_ms": 0, "end_ms": 40_000}], "longer than 30 s"),
        (
            [{"text": "你好", "start_ms": 0, "end_ms": 2000}, {"text": "再见", "start_ms": 1000, "end_ms": 3000}],
            "starts before the previous line ends",
        ),
    ],
)
def test_build_song_rejects_bad_timing(tmp_path, lines, message):
    with pytest.raises(ValueError, match=message):
        build_song(write_song_folder(tmp_path, {"metadata": LYRICS["metadata"], "lines": lines}), make_clips=False)


def test_build_song_rejects_unmatched_translation(tmp_path):
    lyrics = {**LYRICS, "translations": {"不存在的一行": "A line that does not exist"}}
    with pytest.raises(ValueError, match="translation for"):
        build_song(write_song_folder(tmp_path, lyrics), make_clips=False)


def test_build_song_rejects_bad_folder_name(tmp_path):
    folder = tmp_path / "Bad Name"
    folder.mkdir()
    with pytest.raises(ValueError, match="lowercase ASCII"):
        build_song(folder, make_clips=False)


@pytest.mark.parametrize("path", sorted(SONGS.glob("*/lyrics.yaml")), ids=lambda p: p.parent.name)
def test_demo_songs_build(path):
    song = build_song(path.parent, make_clips=False)
    assert song.line_count > 0
    for line in song.lines:
        assert line.translation, line.text
        assert all(word.gloss for word in line.words), line.text


# Shared fixtures (docs/contracts/backend-interfaces.md, section 6)


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "lines"


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")), ids=lambda p: p.stem)
def test_fixture_lines_are_valid(path):
    from app.schemas import Line

    line = Line.model_validate_json(path.read_text(encoding="utf-8"))
    assert line.syllables and line.words
    assert [s.index for s in line.syllables] == list(range(len(line.syllables)))
