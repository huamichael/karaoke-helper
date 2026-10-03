"""Check the session's recordings: names, format, loudness, and what is still missing.

    cd backend && uv run python tests/fixtures/check_recordings.py
    cd backend && uv run python tests/fixtures/check_recordings.py --convert

Looks at every file in tests/fixtures/audio/ and tests/fixtures/tone/.
--convert turns any other format (.m4a, .mp3, .webm, or a WAV at another rate)
into 16 kHz mono WAV and removes the original once the WAV is written.
Exits with 1 if any file needs fixing.

Owner: D. Guide: docs/recording-session.md.
"""

from __future__ import annotations

import argparse
import sys
import wave
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from prompts import RATE, decode, write_wav  # noqa: E402
from session import file_name, parse, takes  # noqa: E402

FOLDERS = ("audio", "tone")
MIN_SECONDS, MAX_SECONDS = 0.4, 30.0
QUIET_PEAK, CLIPPED_PEAK = 0.05, 0.99


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the recording session's files.")
    parser.add_argument("--convert", action="store_true", help="convert other formats to 16 kHz mono WAV")
    args = parser.parse_args(argv)

    expected = {(t.folder, t.item, t.variant) for t in takes()}
    done: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    problems: list[str] = []

    for folder in FOLDERS:
        (HERE / folder).mkdir(exist_ok=True)
        for path in sorted((HERE / folder).iterdir()):
            if path.name.startswith(".") or path.is_dir():
                continue
            where = f"{folder}/{path.name}"
            parsed = parse(path.stem)
            if parsed is None:
                problems.append(f"{where}: name must be <item>__<variant>__<yourname>, e.g. xin1__correct__rayan.wav")
                continue
            item, variant, speaker = parsed
            if (folder, item, variant) not in expected:
                problems.append(f"{where}: '{item}__{variant}' is not in the session list; check the spelling")
                continue

            if path.suffix.lower() != ".wav" or not _is_16k_mono(path):
                if not args.convert:
                    problems.append(f"{where}: not 16 kHz mono WAV; run again with --convert")
                    continue
                target = path.with_suffix(".wav")
                samples = decode(path)
                write_wav(target, samples)
                if target != path:
                    path.unlink()
                print(f"converted {where} -> {target.name}")
                path = target

            issue = _quality(decode(path))
            if issue:
                problems.append(f"{folder}/{path.name}: {issue}; please record it again")
                continue
            done[speaker].add((folder, item, variant))

    print(f"\n{'speaker':<12}{'done':>6}{'left':>6}")
    for speaker in sorted(done):
        print(f"{speaker:<12}{len(done[speaker]):>6}{len(expected) - len(done[speaker]):>6}")
    if not done:
        print("(no recordings yet)")
    for speaker in sorted(done):
        left = [t for t in takes() if (t.folder, t.item, t.variant) not in done[speaker]]
        if left:
            print(f"\n{speaker} still needs:")
            for take in left:
                print(f"  {take.folder}/{file_name(take, speaker)}")

    if problems:
        print("\nTo fix:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    return 0


def _is_16k_mono(path: Path) -> bool:
    try:
        with wave.open(str(path), "rb") as audio:
            return audio.getframerate() == RATE and audio.getnchannels() == 1 and audio.getsampwidth() == 2
    except (wave.Error, EOFError):
        return False


def _quality(samples: np.ndarray) -> str | None:
    seconds = len(samples) / RATE
    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
    if seconds < MIN_SECONDS:
        return f"only {seconds:.1f} s long"
    if seconds > MAX_SECONDS:
        return f"{seconds:.0f} s long; the limit is 30 s"
    if peak < QUIET_PEAK:
        return "almost silent; move closer to the microphone"
    if peak >= CLIPPED_PEAK:
        return "too loud and distorted; move back from the microphone"
    return None


if __name__ == "__main__":
    sys.exit(main())
