"""Runtime configuration and layer switches.

Reads GRADER, WHISPER_ENGINE, ENABLE_CTC, ENABLE_RHYTHM and ENABLE_TONE from the
environment and provides layers_for(target, mode, syllable_count), which says
which grading layers run for an attempt.

Owner: B. Spec: docs/contracts/backend-interfaces.md, section 4.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Literal

GRADERS = ("mock", "real")
WHISPER_ENGINES = ("mlx", "faster")
LAYER_FLAGS = ("ENABLE_CTC", "ENABLE_RHYTHM", "ENABLE_TONE")
# Experiments for manual testing, off by default. TONE_REFERENCE compares tone with the
# word's reference clip.
EXPERIMENT_FLAGS = ("TONE_REFERENCE",)

# backend-interfaces.md section 4: (ctc_spans, ctc_scores, rhythm, tone)
_LINE = {
    "spoken": (False, False, False, False),
    "singing": (True, True, True, False),
}


@dataclass(frozen=True)
class Layers:
    ctc_spans: bool
    ctc_scores: bool
    rhythm: bool
    tone: bool


def grader() -> Literal["mock", "real"]:
    value = os.environ.get("GRADER", "real")
    if value == "mock":
        return "mock"
    if value == "real":
        return "real"
    raise ValueError(f"GRADER must be one of {GRADERS}, got {value!r}")


def whisper_engine() -> Literal["mlx", "faster"]:
    value = os.environ.get("WHISPER_ENGINE")
    if value is None:
        return "mlx" if sys.platform == "darwin" else "faster"
    if value == "faster":
        return "faster"
    if value == "mlx":
        if sys.platform != "darwin":
            raise ValueError("WHISPER_ENGINE=mlx only works on macOS")
        return "mlx"
    raise ValueError(f"WHISPER_ENGINE must be one of {WHISPER_ENGINES}, got {value!r}")


def flag(name: str) -> bool:
    value = os.environ.get(name, "0")
    if value not in ("0", "1"):
        raise ValueError(f"{name} must be '0' or '1', got {value!r}")
    return value == "1"


def validate_layer_flags() -> None:
    for name in LAYER_FLAGS + EXPERIMENT_FLAGS:
        flag(name)


def whisper_prompt() -> str | None:
    """WHISPER_PROMPT, an experiment: text Whisper treats as coming just before the recording."""
    return os.environ.get("WHISPER_PROMPT") or None


def layers_for(target: str, mode: str | None, syllable_count: int = 1) -> Layers:
    if target == "line":
        if mode not in _LINE:
            raise ValueError("mode must be 'spoken' or 'singing' when target is 'line'")
        wanted = _LINE[mode]
    elif target == "word":
        if syllable_count < 1:
            raise ValueError("syllable_count must be at least 1 when target is 'word'")
        # One syllable: tone only. Two or more: CTC spans (for those tones) plus tone.
        wanted = (False, False, False, True) if syllable_count == 1 else (True, False, False, True)
    else:
        raise ValueError("target must be 'line' or 'word'")
    ctc, rhythm, tone = flag("ENABLE_CTC"), flag("ENABLE_RHYTHM"), flag("ENABLE_TONE")
    return Layers(
        ctc_spans=ctc and wanted[0],
        ctc_scores=ctc and wanted[1],
        rhythm=rhythm and wanted[2],
        tone=tone and wanted[3],
    )
