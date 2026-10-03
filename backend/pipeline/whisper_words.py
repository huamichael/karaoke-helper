"""Isolated-word Whisper experiment.

Runs Whisper on words spoken on their own, once with vad_filter on and once off,
and counts how often it hears the word, something else, or nothing. Answers the
risk "Whisper is less reliable on very short clips" in docs/PROJECT_PLAN.md.

Recordings are named <hanzi>.<ext> or <hanzi>__<variant>.<ext>, e.g. 我__michael.m4a.
Without recordings, --tts makes the default words with the macOS Tingting voice;
synthetic speech is cleaner than a learner, so treat those numbers as a best case.

    uv run python -m pipeline.whisper_words --tts
    uv run python -m pipeline.whisper_words path/to/recordings

Owner: B.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Literal

from app import mandarin
from app.audio import BadAudio, load_audio
from app.scoring.transcribe import heard_text, warmup

Outcome = Literal["exact", "same_sound", "other", "empty"]
OUTCOMES: tuple[Outcome, ...] = ("exact", "same_sound", "other", "empty")
AUDIO_SUFFIXES = {".wav", ".m4a", ".mp3", ".aiff", ".webm", ".ogg", ".flac"}

WORDS = ("我", "你", "是", "四", "十", "吃", "七", "想", "女", "绿",
         "老虎", "两只", "一起", "朋友", "唱歌", "喜欢", "中国", "谢谢", "知道", "跑得快")


def expected_of(path: Path) -> str:
    return path.stem.split("__")[0]


def _sounds(text: str) -> list[tuple[str, str]] | None:
    try:
        return [(s.initial, s.final) for s in mandarin.to_syllables(text)]
    except NotImplementedError:
        return None


def classify(expected: str, heard: str) -> Outcome:
    if not heard:
        return "empty"
    if heard == expected:
        return "exact"
    want = _sounds(expected)
    if want is not None and want == _sounds(heard):
        return "same_sound"
    return "other"


def tally(outcomes: list[Outcome]) -> dict[Outcome, int]:
    counts = Counter(outcomes)
    return {o: counts[o] for o in OUTCOMES}


def tts_recordings(words: tuple[str, ...], folder: Path) -> list[Path]:
    paths = []
    for word in words:
        path = folder / f"{word}__tts.aiff"
        subprocess.run(["say", "-v", "Tingting", "-o", str(path), word], check=True)
        paths.append(path)
    return paths


def run(paths: list[Path]) -> None:
    warmup()
    results: dict[bool, list[Outcome]] = {True: [], False: []}
    seconds: dict[bool, float] = {True: 0.0, False: 0.0}
    print(f"{'file':<24} {'vad on':<16} {'vad off':<16}")
    for path in paths:
        try:
            audio = load_audio(path.read_bytes())
        except BadAudio as e:
            print(f"{path.name:<24} skipped: {e}")
            continue
        cells = []
        for vad in (True, False):
            os.environ["WHISPER_VAD"] = "1" if vad else "0"
            start = time.perf_counter()
            heard = heard_text(audio)
            seconds[vad] += time.perf_counter() - start
            outcome = classify(expected_of(path), heard)
            results[vad].append(outcome)
            cells.append(f"{heard or '-'} ({outcome})")
        print(f"{path.name:<24} {cells[0]:<16} {cells[1]:<16}")
    for vad in (True, False):
        n = len(results[vad])
        counts = ", ".join(f"{o} {c}" for o, c in tally(results[vad]).items())
        print(f"vad {'on ' if vad else 'off'}: {counts} of {n}; {seconds[vad] / max(n, 1):.2f}s per word")
    if _sounds("我") is None:
        print("to_syllables is not implemented yet, so homophones count as 'other'; check them by eye.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", nargs="?", type=Path, help="folder of recordings named <hanzi>[__variant].<ext>")
    parser.add_argument("--tts", action="store_true", help="synthesize the default words with macOS say")
    args = parser.parse_args()
    if args.tts:
        with tempfile.TemporaryDirectory() as tmp:
            run(tts_recordings(WORDS, Path(tmp)))
    elif args.folder:
        run(sorted(p for p in args.folder.iterdir() if p.suffix.lower() in AUDIO_SUFFIXES))
    else:
        parser.error("give a folder of recordings or --tts")


if __name__ == "__main__":
    main()
