"""Audio ingest.

Provides load_audio: decodes an uploaded recording (webm/opus, mp4 or wav),
resamples it to 16 kHz mono, trims silence, and returns an Audio object. Raises
BadAudio when the bytes cannot be decoded.

Owner: B. Spec: docs/contracts/backend-interfaces.md, section 3.
"""

from __future__ import annotations

import io

import numpy as np
from faster_whisper import decode_audio

from app.schemas import Audio

SAMPLE_RATE = 16000
MAX_SECONDS = 30
MARGIN_MS = 150
FRAME_MS = 20
# A frame is silent when its RMS is below both of these. Tune on saved attempts.
SILENCE_FLOOR = 0.003
SILENCE_RATIO = 0.1


class BadAudio(Exception):
    pass


class AudioTooLong(BadAudio):
    pass


def load_audio(data: bytes) -> Audio:
    if not data:
        raise BadAudio("The recording is empty.")
    try:
        samples = decode_audio(io.BytesIO(data), sampling_rate=SAMPLE_RATE)
    except Exception as e:
        raise BadAudio("The recording could not be decoded.") from e
    if samples.size == 0:
        raise BadAudio("The recording contains no audio.")
    if samples.size > MAX_SECONDS * SAMPLE_RATE:
        raise AudioTooLong(f"The recording is longer than {MAX_SECONDS} seconds.")

    start, end = _voiced_bounds(samples)
    return Audio(samples=samples[start:end], sample_rate=SAMPLE_RATE, trim_offset_ms=start * 1000 // SAMPLE_RATE)


def _voiced_bounds(samples: np.ndarray) -> tuple[int, int]:
    """Sample range from the first to the last voiced frame, plus the margin. All of it if nothing is voiced."""
    frame = SAMPLE_RATE * FRAME_MS // 1000
    count = len(samples) // frame
    if count == 0:
        return 0, len(samples)
    rms = np.sqrt(np.mean(samples[: count * frame].reshape(count, frame) ** 2, axis=1))
    voiced = np.flatnonzero(rms > max(SILENCE_FLOOR, SILENCE_RATIO * float(rms.max())))
    if voiced.size == 0:
        return 0, len(samples)
    margin = SAMPLE_RATE * MARGIN_MS // 1000
    start = max(0, int(voiced[0]) * frame - margin)
    end = min(len(samples), (int(voiced[-1]) + 1) * frame + margin)
    return start, end
