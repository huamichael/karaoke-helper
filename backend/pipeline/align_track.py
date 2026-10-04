"""Add original-track syllable timings with the user-recording aligner (C).

    uv run python -m pipeline.align_track --song <id> [--vocals vocals.wav]

The vocal file must share the original track's time origin. Writes are atomic;
failed runs leave the original bundle intact. No silence trimming is performed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import tempfile

import numpy as np

from app.schemas import Audio, Song
from app.scoring.ctc import SAMPLE_RATE, align

SONGS_DIR = Path(__file__).resolve().parents[2] / "data" / "songs"
CONTEXT_MS = 200


def decode_track(path: Path) -> np.ndarray:
    """Decode with bundled PyAV, avoiding system ffmpeg and torchaudio I/O."""
    import av

    chunks = []
    with av.open(str(path)) as container:
        resampler = av.AudioResampler(format="fltp", layout="mono", rate=SAMPLE_RATE)
        for frame in container.decode(audio=0):
            chunks.extend(output.to_ndarray().reshape(-1) for output in resampler.resample(frame))
        chunks.extend(output.to_ndarray().reshape(-1) for output in resampler.resample(None))
    if not chunks:
        raise ValueError(f"No audio in {path}")
    return np.concatenate(chunks).astype(np.float32)


def align_song(song: Song, samples: np.ndarray) -> tuple[Song, list[str]]:
    """Pure bundle transformation; model errors never partially write a song."""
    updated = song.model_copy(deep=True)
    reports = []
    for line in updated.lines:
        if not 0 <= line.start_ms < line.end_ms:
            raise ValueError(f"Line {line.index} has invalid bounds")
        first = max(0, (line.start_ms - CONTEXT_MS) * SAMPLE_RATE // 1000)
        last = min(len(samples), (line.end_ms + CONTEXT_MS) * SAMPLE_RATE // 1000)
        if first >= last or line.end_ms * SAMPLE_RATE // 1000 > len(samples):
            raise ValueError(f"Line {line.index} extends beyond the selected track")
        audio = Audio(samples=samples[first:last], sample_rate=SAMPLE_RATE, trim_offset_ms=0)
        spans = align(audio, line.syllables)
        if len(spans) != len(line.syllables):
            raise ValueError(f"Line {line.index}: align violated the per-syllable list rule")
        offset_ms = first * 1000 // SAMPLE_RATE
        confidences = []
        for syllable, span in zip(line.syllables, spans):
            if span is None:
                syllable.start_ms = syllable.end_ms = None
                continue
            if not 0 <= span.start_ms < span.end_ms <= len(audio.samples) * 1000 / SAMPLE_RATE:
                raise ValueError(f"Line {line.index}: invalid aligned span")
            syllable.start_ms = offset_ms + span.start_ms
            syllable.end_ms = offset_ms + span.end_ms
            confidences.append(span.confidence)
        mean = f"{np.mean(confidences):.3f}" if confidences else "unavailable"
        reports.append(f"line {line.index}: confidence={mean}, missing={len(spans) - len(confidences)}/{len(spans)} {line.text}")
    # Revalidate assignments and the complete serialized bundle before writing.
    return Song.model_validate(updated.model_dump()), reports


def write_atomic(path: Path, song: Song, original: str) -> None:
    """Avoid clobbering a concurrently edited bundle or leaving partial JSON."""
    serialized = json.dumps(song.model_dump(), ensure_ascii=False, indent=2) + "\n"
    Song.model_validate_json(serialized)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        if path.read_text(encoding="utf-8") != original:
            raise RuntimeError("song.json changed during alignment; rerun against the updated bundle")
        temporary.chmod(path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--song", required=True, help="song folder id")
    parser.add_argument("--vocals", type=Path, help="isolated vocals with the same time origin")
    parser.add_argument("--dry-run", action="store_true", help="report timings without replacing song.json")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.song):
        parser.error("--song must be a lowercase song id")
    path = SONGS_DIR / args.song / "song.json"
    try:
        original = path.read_text(encoding="utf-8")
        song = Song.model_validate_json(original)
        if song.id != args.song:
            raise ValueError("Song id does not match its folder")
        samples = decode_track(args.vocals or path.parent / "audio.mp3")
        updated, reports = align_song(song, samples)
        for report in reports:
            print(report)
        if not args.dry_run:
            write_atomic(path, updated, original)
            print(f"Wrote {path}. Review low-confidence lines before enabling rhythm.")
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Alignment failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
