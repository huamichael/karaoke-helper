"""Runtime configuration and layer switches.

Reads GRADER, WHISPER_ENGINE, ENABLE_CTC, ENABLE_RHYTHM and ENABLE_TONE from the
environment and provides layers_for(target, mode), which says which grading
layers run for an attempt.

Owner: B. Spec: docs/contracts/backend-interfaces.md, section 4.
"""

import os
import sys
from typing import Literal

GRADERS = ("mock", "real")
WHISPER_ENGINES = ("mlx", "faster")


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
