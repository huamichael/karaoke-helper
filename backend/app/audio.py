"""Audio ingest.

Provides load_audio: decodes an uploaded recording (webm/opus, mp4 or wav),
resamples it to 16 kHz mono, trims silence, and returns an Audio object. Raises
BadAudio when the bytes cannot be decoded.

Owner: B. Spec: docs/contracts/backend-interfaces.md, section 3.
"""

from __future__ import annotations

from app.schemas import Audio


class BadAudio(Exception):
    pass


def load_audio(data: bytes) -> Audio:
    raise NotImplementedError
