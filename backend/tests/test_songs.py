"""Tests for the song store in app/songs.py.

Loads the real demo bundle, and broken copies of it written to a temporary
folder, so every rule in data-model.md section 5 has a failing case.

Owner: B.
"""

import copy
import json
from pathlib import Path

import pytest

from app import songs
from app.songs import InvalidSong, NotFound

DEMO = json.loads((songs.SONGS_DIR / "demo" / "song.json").read_text(encoding="utf-8"))


def write_song(root: Path, data: dict, song_id: str = "demo") -> Path:
    folder = root / song_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "song.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return root


def broken(change) -> dict:
    data = copy.deepcopy(DEMO)
    change(data)
    return data


# --- happy path: the real demo bundle ---------------------------------------


def test_demo_song_loads():
    song = songs.get_song("demo")
    assert (song.id, song.line_count, len(song.lines)) == ("demo", 2, 2)
    assert [s.hanzi for s in song.lines[1].syllables] == list("跑得快跑得快")


def test_list_songs_includes_demo_summary():
    summary = next(s for s in songs.list_songs() if s.id == "demo")
    assert summary.model_dump() == {"id": "demo", "title": "两只老虎", "artist": "Traditional", "line_count": 2}


def test_get_line_and_word():
    song = songs.get_song("demo")
    line = songs.get_line(song, 1)
    assert line.text == "跑得快，跑得快"
    word = songs.get_word(line, 1)
    assert (word.text, word.syllable_indices) == ("跑得快", [3, 4, 5])


def test_word_syllables_in_order():
    line = songs.get_line(songs.get_song("demo"), 0)
    sylls = songs.word_syllables(line, 3)
    assert [(s.index, s.hanzi, s.pinyin_numeric) for s in sylls] == [(6, "老", "lao3"), (7, "虎", "hu3")]


# --- boundaries ---------------------------------------------------------------


def test_last_line_and_word_accepted():
    song = songs.get_song("demo")
    assert songs.get_line(song, 1).index == 1
    assert songs.get_word(song.lines[0], 3).index == 3


@pytest.mark.parametrize("index", [2, -1, 99])
def test_line_index_out_of_range(index):
    with pytest.raises(NotFound) as e:
        songs.get_line(songs.get_song("demo"), index)
    assert e.value.code == "line_not_found"


@pytest.mark.parametrize("index", [4, -1])
def test_word_index_out_of_range(index):
    line = songs.get_song("demo").lines[0]
    for call in (songs.get_word, songs.word_syllables):
        with pytest.raises(NotFound) as e:
            call(line, index)
        assert e.value.code == "word_not_found"


def test_empty_or_missing_root_lists_nothing(tmp_path):
    assert songs.list_songs(tmp_path) == []
    assert songs.list_songs(tmp_path / "nope") == []


def test_list_skips_folders_without_song_json_or_with_bad_names(tmp_path):
    write_song(tmp_path, DEMO)
    (tmp_path / "empty").mkdir()
    (tmp_path / "bad name").mkdir()
    (tmp_path / "bad name" / "song.json").write_text("{}", encoding="utf-8")
    assert [s.id for s in songs.list_songs(tmp_path)] == ["demo"]


# --- failures -----------------------------------------------------------------


@pytest.mark.parametrize("song_id", ["nope", "../songs", "demo/..", "", "de mo"])
def test_unknown_or_unsafe_song_id(song_id):
    with pytest.raises(NotFound) as e:
        songs.get_song(song_id)
    assert e.value.code == "song_not_found"


def test_song_id_cannot_reach_a_bundle_outside_the_root(tmp_path):
    root = tmp_path / "songs"
    root.mkdir()
    write_song(tmp_path, broken(_set(["id"], "outside")), song_id="outside")
    assert (root / ".." / "outside" / "song.json").is_file()
    with pytest.raises(NotFound) as e:
        songs.get_song("../outside", root)
    assert e.value.code == "song_not_found"


def test_malformed_json(tmp_path):
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "song.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(InvalidSong):
        songs.get_song("demo", tmp_path)


def _set(path: list, value):
    def change(data):
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
    return change


def _pop(path: list):
    def change(data):
        target = data
        for key in path[:-1]:
            target = target[key]
        target.pop(path[-1])
    return change


@pytest.mark.parametrize("change, message", [
    (_set(["lines", 0, "syllables", 0, "pinyin_num"], "liang3"), "pinyin_num"),
    (_set(["lines", 0, "syllables", 0, "tone"], None), "tone"),
    (_set(["id"], "other"), "folder"),
    (_set(["line_count"], 3), "line_count"),
    (_set(["lines", 1, "index"], 0), "line 1 has index"),
    (_set(["lines", 0, "syllables", 2, "index"], 5), "syllable 2 has index"),
    (_set(["lines", 0, "syllables", 2, "hanzi"], "，"), "not one Hanzi"),
    (_set(["lines", 0, "syllables", 2, "hanzi"], "老老"), "not one Hanzi"),
    (_set(["lines", 0, "text"], "两只老虎，两只狮子"), "does not match text"),
    (_set(["lines", 0, "words", 1, "index"], 7), "word 1 has index"),
    (_set(["lines", 0, "words", 1, "syllable_indices"], [2, 9]), "out of range"),
    (_set(["lines", 0, "syllables", 3, "word_index"], 0), "word_index 1"),
    (_set(["lines", 0, "words", 1, "text"], "老鼠"), "does not match its syllables"),
    (_pop(["lines", 0, "words", 3]), "cover every syllable"),
], ids=lambda x: x if isinstance(x, str) else "")
def test_invalid_bundle_rejected(tmp_path, change, message):
    write_song(tmp_path, broken(change))
    with pytest.raises(InvalidSong, match=message):
        songs.get_song("demo", tmp_path)


def test_unchanged_copy_of_demo_is_valid(tmp_path):
    write_song(tmp_path, copy.deepcopy(DEMO))
    assert songs.get_song("demo", tmp_path).model_dump() == songs.get_song("demo").model_dump()
