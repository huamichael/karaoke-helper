"""Karaoke tracks: each song without its singer, for Karaoke mode.

Command-line tool. Separates a song's audio.mp3 with Demucs (pipeline.separate),
writes everything but the voice to data/songs/<id>/instrumental.mp3, and sets
instrumental_url in that song's song.json. The voice separated on the way is kept
as check/vocals.wav for line_ends, so no song is separated twice.

    uv run --group vocals python -m pipeline.instrumental --song jasmine-flower
    uv run --group vocals python -m pipeline.instrumental --all

A song that already has its instrumental is only re-linked, unless --force. The
instrumental is cut from a copyrighted track, so git ignores it: share it with the
song bundle, outside git. Without it, Karaoke mode plays the original track.

Owner: D. Spec: docs/tasks/backend-songs-tone.md ("Instrumentals").
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import av
import numpy as np

from app.schemas import Song
from pipeline.build_song import INSTRUMENTAL, SONGS_DIR, instrumental_url, write_song

BIT_RATE = 192_000


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Make each song's karaoke track (the song without its singer).")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--song", help="song folder name under data/songs/")
    which.add_argument("--all", action="store_true", help="every song folder that has an audio.mp3")
    parser.add_argument("--force", action="store_true", help="separate again even if instrumental.mp3 exists")
    args = parser.parse_args(argv)

    folders = sorted(p.parent for p in SONGS_DIR.glob("*/audio.mp3")) if args.all else [SONGS_DIR / args.song]
    for folder in folders:
        out = folder / INSTRUMENTAL
        if not (folder / "audio.mp3").exists():
            print(f"{folder.name}: no audio.mp3, so no instrumental", file=sys.stderr)
        elif out.exists() and not args.force:
            print(f"{folder.name}: {INSTRUMENTAL} already made (--force to make it again)")
        else:
            from pipeline.separate import save_voice, separate

            stems = separate(folder)
            write_mp3(out, stems.instrumental, stems.rate)
            if not (folder / "check" / "vocals.wav").exists():
                save_voice(folder, stems.voice)
            print(f"{folder.name}: wrote {out.relative_to(SONGS_DIR.parent.parent)}")
        link(folder)
    return 0


def link(folder: Path) -> None:
    """Set song.json's instrumental_url from whether the file is there (null when it is not)."""
    path = folder / "song.json"
    if not path.exists():
        return
    song = Song.model_validate_json(path.read_text(encoding="utf-8"))
    song.instrumental_url = instrumental_url(folder)
    write_song(folder, song)


def write_mp3(path: Path, stereo: np.ndarray, rate: int, bit_rate: int = BIT_RATE) -> None:
    """Encode float stereo audio, shape (2, n) in [-1, 1], as MP3 with PyAV's bundled LAME."""
    pcm = np.ascontiguousarray(np.clip(stereo, -1, 1), dtype=np.float32)
    tmp = path.with_suffix(".part.mp3")
    with av.open(str(tmp), "w", format="mp3") as out:
        stream = out.add_stream("libmp3lame", rate=rate, layout="stereo")
        stream.bit_rate = bit_rate
        step = 1152 * 64
        for start in range(0, pcm.shape[1], step):
            frame = av.AudioFrame.from_ndarray(pcm[:, start:start + step], format="fltp", layout="stereo")
            frame.sample_rate = rate
            frame.pts = start
            for packet in stream.encode(frame):
                out.mux(packet)
        for packet in stream.encode(None):
            out.mux(packet)
    tmp.replace(path)  # a run stopped half way leaves no half-written instrumental behind


if __name__ == "__main__":
    sys.exit(main())
