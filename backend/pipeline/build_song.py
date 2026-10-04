"""Pipeline step 1: build a song bundle.

Command-line tool. Turns a song folder's lyrics.yaml into
data/songs/<song_id>/song.json: lines, syllables and words, with a spoken clip
for each word. Keeps syllable times that align_track already filled in.

    uv run python -m pipeline.build_song --id yi-jian-mei
    uv run python -m pipeline.build_song --all --no-clips
    uv run python -m pipeline.build_song --id yi-jian-mei --check

Owner: D. Spec: docs/contracts/data-model.md, section 5; docs/tasks/backend-songs-tone.md.
"""

import argparse
import asyncio
import json
import re
import sys
import wave
from pathlib import Path

import numpy as np
import yaml

from app.mandarin import segment_words, to_syllables
from app.schemas import Line, LyricSyllable, Song, Word

SONGS_DIR = Path(__file__).resolve().parents[2] / "data" / "songs"
MEDIA_PREFIX = "/media/songs"           # B serves data/songs/ at this path
VOICE = "zh-CN-XiaoxiaoNeural"          # edge-tts voice for the spoken word clips
RATE = "-20%"                           # slower than her default, easier to learn from
MAX_LINE_MS = 30_000                    # a user recording is capped at 30 s
LONG_LINE_MS = 12_000                   # longer lines are hard to sing back and grade
_SONG_ID = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


def reading_overrides(texts: list[str], readings: dict[str, str]) -> list[dict[int, str]]:
    """Turn a song's phrase readings into per-line overrides for to_syllables.

    readings is the `readings` block of lyrics.yaml: each phrase maps to one
    pinyin_numeric reading per character, separated by spaces, for example
    {"掩没": "yan3 mo4"}. Every occurrence of the phrase in every line is fixed.

    Returns one overrides dict per text, in order, keyed by character position.

    Raises ValueError if a phrase is not all Hanzi, if its reading has the wrong
    number of syllables, if it matches no line (usually a typo, or Simplified
    against Traditional characters), or if two phrases give one character
    different readings.
    """
    overrides: list[dict[int, str]] = [{} for _ in texts]
    for phrase, reading in readings.items():
        syllables = str(reading).split()
        if not phrase or len(to_syllables(phrase)) != len(phrase):
            raise ValueError(f"reading phrase {phrase!r} must contain only Hanzi")
        if len(syllables) != len(phrase):
            raise ValueError(
                f"reading for {phrase!r} has {len(syllables)} syllables, expected {len(phrase)}: {reading!r}"
            )

        found = False
        for line_overrides, text in zip(overrides, texts):
            start = text.find(phrase)
            while start != -1:
                found = True
                for offset, syllable in enumerate(syllables):
                    previous = line_overrides.setdefault(start + offset, syllable)
                    if previous != syllable:
                        raise ValueError(
                            f"conflicting readings for {text[start + offset]!r} in {text!r}: {previous} and {syllable}"
                        )
                start = text.find(phrase, start + len(phrase))
        if not found:
            raise ValueError(f"reading for {phrase!r} matches no line of the song")
    return overrides


def word_splits(texts: list[str], fixes: dict[str, str]) -> list[list[str]]:
    """Split each line into words, applying the song's word fixes.

    fixes is the `words` block of lyrics.yaml: each phrase maps to its words,
    separated by spaces, for example {"又香又白人人誇": "又 香 又 白 人人 誇"}.
    The rest of each line is split by segment_words, and any word of four or
    more characters it returns is split into pairs (爱我所爱 becomes 爱我 所爱).

    Raises ValueError if a phrase is not all Hanzi, if its words do not join
    back into the phrase, or if it matches no line.
    """
    for phrase, split in fixes.items():
        if not phrase or len(to_syllables(phrase)) != len(phrase):
            raise ValueError(f"word fix {phrase!r} must contain only Hanzi")
        if "".join(str(split).split()) != phrase:
            raise ValueError(f"word fix for {phrase!r} does not join back into the phrase: {split!r}")
    unused = set(fixes)

    result = []
    for text in texts:
        words: list[str] = []
        position = 0
        while position < len(text):
            phrase = _fix_at(text, position, fixes)
            if phrase:
                unused.discard(phrase)
                words.extend(str(fixes[phrase]).split())
                position += len(phrase)
                continue
            end = _next_fix(text, position, fixes)
            for word in segment_words(text[position:end]):
                words.extend(_pairs(word))
            position = end
        result.append(words)

    if unused:
        raise ValueError(f"word fix for {sorted(unused)[0]!r} matches no line of the song")
    return result


def build_song(folder: Path, make_clips: bool = True) -> Song:
    """Build the Song for one song folder. Does not write song.json.

    Prints warnings to stderr. Raises ValueError when lyrics.yaml is invalid.
    """
    song_id = folder.name
    if not _SONG_ID.fullmatch(song_id):
        raise ValueError(f"song folder name {song_id!r} must be lowercase ASCII words joined by '-'")
    lyrics = _load_lyrics(folder / "lyrics.yaml")
    if not (folder / "audio.mp3").exists():
        _warn(f"{song_id}: audio.mp3 is missing; the frontend cannot play this song")

    entries = [line for line in lyrics["lines"] if line["text"].strip()]
    texts = [line["text"] for line in entries]
    overrides = reading_overrides(texts, lyrics.get("readings") or {})
    words = word_splits(texts, lyrics.get("words") or {})
    translations = lyrics.get("translations") or {}
    glosses = lyrics.get("glosses") or {}
    for text in translations:
        if text not in texts:
            raise ValueError(f"translation for {text!r} matches no line of the song")

    lines = []
    for index, (entry, line_overrides, line_words) in enumerate(zip(entries, overrides, words)):
        syllables = to_syllables(entry["text"], line_overrides)
        lines.append(_line(index, entry, syllables, line_words, translations.get(entry["text"]), glosses))

    used_words = {word.text for line in lines for word in line.words}
    for word in glosses:
        if word not in used_words:
            _warn(f"{song_id}: gloss for {word!r} matches no word; check the words block")

    clips = _clip_texts(lines)
    if make_clips:
        _generate_clips(folder / "words", clips)
    for line in lines:
        for word in line.words:
            key = _clip_key(line, word)
            if (folder / "words" / f"{key}.mp3").exists():
                word.audio_url = f"{MEDIA_PREFIX}/{song_id}/words/{key}.mp3"

    song = Song(
        id=song_id,
        title=str(lyrics["metadata"]["title"]),
        artist=str(lyrics["metadata"]["artist"]),
        line_count=len(lines),
        audio_url=f"{MEDIA_PREFIX}/{song_id}/audio.mp3",
        lines=lines,
    )
    _keep_aligned_times(song, folder / "song.json")
    return song


def write_song(folder: Path, song: Song) -> None:
    """Write song.json into the song folder."""
    text = json.dumps(song.model_dump(), ensure_ascii=False, indent=2)
    (folder / "song.json").write_text(text + "\n", encoding="utf-8")


def review_table(song: Song, fixed: set[tuple[int, int]] | None = None) -> str:
    """A table of every line's Hanzi, pinyin and words, for the human review."""
    rows = [f"{song.title} ({song.id}): {song.line_count} lines"]
    for line in song.lines:
        seconds = f"{line.start_ms / 1000:6.2f}-{line.end_ms / 1000:6.2f}s"
        pinyin = " ".join(
            s.pinyin + ("*" if fixed and (line.index, s.index) in fixed else "") for s in line.syllables
        )
        words = " / ".join(word.text for word in line.words)
        rows.append(f"{line.index:3} {seconds}  {line.text}\n      {pinyin}\n      {words}")
    if fixed:
        rows.append("* reading fixed in lyrics.yaml")
    return "\n".join(rows)


def export_check_clips(folder: Path, song: Song) -> Path:
    """Cut each line out of audio.mp3 into check/<line>.wav, for listening."""
    import av  # only needed here

    rate = 22_050
    chunks = []
    with av.open(str(folder / "audio.mp3")) as container:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=rate)
        for frame in container.decode(audio=0):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray().reshape(-1))
        for out in resampler.resample(None):
            chunks.append(out.to_ndarray().reshape(-1))
    samples = np.concatenate(chunks)

    out_dir = folder / "check"
    out_dir.mkdir(exist_ok=True)
    for line in song.lines:
        clip = samples[line.start_ms * rate // 1000 : line.end_ms * rate // 1000]
        with wave.open(str(out_dir / f"{line.index:02}.wav"), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(clip.astype("<i2").tobytes())
    return out_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build song.json from a song folder's lyrics.yaml.")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--id", help="song folder name under data/songs/")
    which.add_argument("--all", action="store_true", help="build every song folder")
    parser.add_argument("--no-clips", action="store_true", help="do not generate spoken word clips (no internet needed)")
    parser.add_argument("--check", action="store_true", help="also cut each line to check/<line>.wav for listening")
    args = parser.parse_args(argv)

    folders = sorted(p.parent for p in SONGS_DIR.glob("*/lyrics.yaml")) if args.all else [SONGS_DIR / args.id]
    failed = False
    for folder in folders:
        try:
            if not (folder / "lyrics.yaml").exists():
                raise ValueError(f"{folder} has no lyrics.yaml")
            song = build_song(folder, make_clips=not args.no_clips)
            write_song(folder, song)
            print(review_table(song, _fixed_positions(folder)))
            missing = sum(1 for line in song.lines for word in line.words if word.audio_url is None)
            if missing:
                _warn(f"{song.id}: {missing} words have no spoken clip; the frontend falls back to speech synthesis")
            if args.check:
                print(f"line clips for listening: {export_check_clips(folder, song)}")
            print(f"wrote {folder / 'song.json'}\n")
        except (ValueError, OSError) as error:
            print(f"error: {folder.name}: {error}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


def _load_lyrics(path: Path) -> dict:
    """Read lyrics.yaml and check its structure. Format: data-model.md, section 5."""
    lyrics = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(lyrics, dict):
        raise ValueError(f"{path} is not a YAML mapping")
    metadata = lyrics.get("metadata") or {}
    for key in ("title", "artist"):
        if not metadata.get(key):
            raise ValueError(f"metadata.{key} is missing")
    for block in ("readings", "words", "translations", "glosses"):
        if not isinstance(lyrics.get(block) or {}, dict):
            raise ValueError(f"{block} must be a mapping of phrase to value")

    previous_end = 0
    lines = lyrics.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValueError("lines is missing or empty")
    for number, line in enumerate(lines, start=1):
        where = f"lines entry {number}"
        if not isinstance(line, dict) or not isinstance(line.get("text"), str):
            raise ValueError(f"{where} needs a text field (use '' for an instrumental gap)")
        start, end = line.get("start_ms"), line.get("end_ms")
        if not line["text"].strip() and end is None and isinstance(start, int):
            end = start + 1  # an instrumental gap may run to the end of the song
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end:
            raise ValueError(f"{where} ({line['text']!r}) needs whole-number start_ms < end_ms")
        if start < previous_end:
            raise ValueError(f"{where} ({line['text']!r}) starts before the previous line ends")
        previous_end = end
        if line["text"].strip():
            if end - start > MAX_LINE_MS:
                raise ValueError(f"{where} ({line['text']!r}) is longer than 30 s; split it")
            if end - start > LONG_LINE_MS:
                _warn(f"{where} ({line['text']!r}) is {(end - start) / 1000:.1f} s long; consider splitting it")
    return lyrics


def _line(index, entry, syllables, words, translation, glosses) -> Line:
    if sum(len(word) for word in words) != len(syllables):
        raise ValueError(f"words {words} do not cover the syllables of {entry['text']!r}")
    lyric_syllables, word_records, position = [], [], 0
    for word_index, text in enumerate(words):
        indices = list(range(position, position + len(text)))
        word_records.append(
            Word(index=word_index, text=text, syllable_indices=indices, gloss=glosses.get(text), audio_url=None)
        )
        for i in indices:
            lyric_syllables.append(LyricSyllable(**syllables[i].model_dump(), index=i, word_index=word_index))
        position += len(text)
    return Line(
        index=index,
        start_ms=entry["start_ms"],
        end_ms=entry["end_ms"],
        text=entry["text"],
        translation=translation,
        syllables=lyric_syllables,
        words=word_records,
    )


def _clip_key(line: Line, word: Word) -> str:
    """Clip file name: the word's reading, so homophones and repeats share one clip."""
    return "-".join(line.syllables[i].pinyin_numeric for i in word.syllable_indices)


def _clip_texts(lines: list[Line]) -> dict[str, str]:
    """Clip file name to the Hanzi spoken in it, one entry per distinct reading."""
    clips: dict[str, str] = {}
    for line in lines:
        for word in line.words:
            clips.setdefault(_clip_key(line, word), word.text)
    return clips


def _generate_clips(out_dir: Path, clips: dict[str, str]) -> None:
    """Generate missing clips with edge-tts. Needs internet; failures only warn."""
    missing = {key: text for key, text in clips.items() if not (out_dir / f"{key}.mp3").exists()}
    if not missing:
        return
    import edge_tts  # only needed here

    out_dir.mkdir(exist_ok=True)
    limit = asyncio.Semaphore(4)

    async def one(key: str, text: str) -> None:
        path = out_dir / f"{key}.mp3"
        async with limit:
            try:
                await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(path))
            except Exception as error:  # network or service failure: keep going without this clip
                path.unlink(missing_ok=True)
                _warn(f"could not generate the clip for {text!r}: {error}")

    async def run() -> None:
        await asyncio.gather(*(one(key, text) for key, text in missing.items()))

    print(f"generating {len(missing)} spoken word clips with {VOICE} at {RATE} ...", file=sys.stderr)
    asyncio.run(run())


def _keep_aligned_times(song: Song, path: Path) -> None:
    """Copy syllable times from the existing song.json for lines that did not change."""
    if not path.exists():
        return
    try:
        old = Song.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError:
        _warn(f"{path} could not be read; syllable times from align_track are not kept")
        return
    previous = {(l.text, l.start_ms, l.end_ms): l for l in old.lines}
    for line in song.lines:
        match = previous.get((line.text, line.start_ms, line.end_ms))
        if match is None or [s.pinyin_numeric for s in match.syllables] != [s.pinyin_numeric for s in line.syllables]:
            continue
        for new, kept in zip(line.syllables, match.syllables):
            new.start_ms, new.end_ms = kept.start_ms, kept.end_ms


def _fixed_positions(folder: Path) -> set[tuple[int, int]]:
    """(line index, syllable index) of every syllable whose reading lyrics.yaml fixes."""
    lyrics = yaml.safe_load((folder / "lyrics.yaml").read_text(encoding="utf-8"))
    texts = [line["text"] for line in lyrics["lines"] if line["text"].strip()]
    fixed = set()
    for index, (text, overrides) in enumerate(zip(texts, reading_overrides(texts, lyrics.get("readings") or {}))):
        positions = sorted(overrides)
        hanzi_positions = [i for i, c in enumerate(text) if to_syllables(c)]
        fixed.update((index, hanzi_positions.index(p)) for p in positions)
    return fixed


def _fix_at(text: str, position: int, fixes: dict[str, str]) -> str | None:
    """The longest word-fix phrase that starts at this position, if any."""
    matches = [phrase for phrase in fixes if text.startswith(phrase, position)]
    return max(matches, key=len) if matches else None


def _next_fix(text: str, position: int, fixes: dict[str, str]) -> int:
    """Where the next word-fix phrase starts after this position, or the end of the text."""
    starts = [text.find(phrase, position + 1) for phrase in fixes]
    return min([s for s in starts if s != -1], default=len(text))


def _pairs(word: str) -> list[str]:
    """Split a word of four or more characters into pairs; shorter words stay whole."""
    if len(word) < 4:
        return [word]
    return [word[i : i + 2] for i in range(0, len(word), 2)]


def _warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
