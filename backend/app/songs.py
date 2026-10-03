"""Song store.

Loads song bundles from data/songs/<song_id>/song.json into Song objects, and
looks up songs, lines and words for the routes and the grader.

Owner: B. Spec: docs/contracts/data-model.md, section 5.
"""

import re
import unicodedata
from pathlib import Path

from pydantic import ValidationError

from app.schemas import Line, LyricSyllable, Song, SongSummary, Word

SONGS_DIR = Path(__file__).resolve().parents[2] / "data" / "songs"

_SONG_ID = re.compile(r"[A-Za-z0-9_-]+")


class NotFound(Exception):
    """An id or index that does not exist. `code` is the api.md error code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class InvalidSong(Exception):
    """A song.json that does not follow data-model.md."""


def list_songs(root: Path = SONGS_DIR) -> list[SongSummary]:
    if not root.is_dir():
        return []
    ids = sorted(p.name for p in root.iterdir() if _SONG_ID.fullmatch(p.name) and (p / "song.json").is_file())
    return [SongSummary(**get_song(i, root).model_dump(include=set(SongSummary.model_fields))) for i in ids]


def get_song(song_id: str, root: Path = SONGS_DIR) -> Song:
    path = root / song_id / "song.json"
    if not _SONG_ID.fullmatch(song_id) or not path.is_file():
        raise NotFound("song_not_found", f"No song with id {song_id!r}.")
    try:
        song = Song.model_validate_json(path.read_bytes())
    except ValidationError as e:
        raise InvalidSong(f"{path}: {e}") from e
    _check(song, song_id, path)
    return song


def get_line(song: Song, line_index: int) -> Line:
    if not 0 <= line_index < len(song.lines):
        raise NotFound("line_not_found", f"Song {song.id!r} has no line {line_index}.")
    return song.lines[line_index]


def get_word(line: Line, word_index: int) -> Word:
    if not 0 <= word_index < len(line.words):
        raise NotFound("word_not_found", f"Line {line.index} has no word {word_index}.")
    return line.words[word_index]


def word_syllables(line: Line, word_index: int) -> list[LyricSyllable]:
    return [line.syllables[i] for i in get_word(line, word_index).syllable_indices]


def is_hanzi(ch: str) -> bool:
    return unicodedata.name(ch, "").startswith("CJK UNIFIED IDEOGRAPH")


def _check(song: Song, song_id: str, path: Path) -> None:
    def fail(message: str) -> None:
        raise InvalidSong(f"{path}: {message}")

    if song.id != song_id:
        fail(f"id is {song.id!r} but the folder is {song_id!r}")
    if song.line_count != len(song.lines):
        fail(f"line_count is {song.line_count} but there are {len(song.lines)} lines")
    for i, line in enumerate(song.lines):
        where = f"line {i}"
        if line.index != i:
            fail(f"{where} has index {line.index}")
        for j, syl in enumerate(line.syllables):
            if syl.index != j:
                fail(f"{where}, syllable {j} has index {syl.index}")
            if len(syl.hanzi) != 1 or not is_hanzi(syl.hanzi):
                fail(f"{where}, syllable {j}: hanzi {syl.hanzi!r} is not one Hanzi character")
        hanzi = "".join(s.hanzi for s in line.syllables)
        if hanzi != "".join(ch for ch in line.text if is_hanzi(ch)):
            fail(f"{where}: syllables spell {hanzi!r}, which does not match text {line.text!r}")
        covered: list[int] = []
        for k, word in enumerate(line.words):
            if word.index != k:
                fail(f"{where}, word {k} has index {word.index}")
            if any(not 0 <= n < len(line.syllables) for n in word.syllable_indices):
                fail(f"{where}, word {k}: syllable_indices {word.syllable_indices} out of range")
            if any(line.syllables[n].word_index != k for n in word.syllable_indices):
                fail(f"{where}, word {k}: its syllables do not all have word_index {k}")
            if word.text != "".join(line.syllables[n].hanzi for n in word.syllable_indices):
                fail(f"{where}, word {k}: text {word.text!r} does not match its syllables")
            covered.extend(word.syllable_indices)
        if covered != list(range(len(line.syllables))):
            fail(f"{where}: words must cover every syllable once, in order; got {covered}")
