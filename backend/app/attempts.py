"""Saved attempts, for tuning thresholds later.

Provides save: writes a graded recording to data/attempts/<attempt_id>.wav
(16 kHz mono, after silence trimming) and the request and result beside it as
<attempt_id>.json. Git ignores the folder.

Owner: B. Spec: docs/tasks/backend-api-whisper.md, block 2.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

from app.schemas import AttemptResult, Audio

ATTEMPTS_DIR = Path(__file__).resolve().parents[2] / "data" / "attempts"


def save(audio: Audio, result: AttemptResult, root: Path | None = None) -> None:
    root = root or ATTEMPTS_DIR
    root.mkdir(parents=True, exist_ok=True)
    write_wav(root / f"{result.attempt_id}.wav", audio)
    record = {"trim_offset_ms": audio.trim_offset_ms, "result": result.model_dump()}
    (root / f"{result.attempt_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def write_wav(path: Path, audio: Audio) -> None:
    pcm = (np.clip(audio.samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(audio.sample_rate)
        w.writeframes(pcm.tobytes())
