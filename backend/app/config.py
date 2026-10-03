"""Runtime configuration and layer switches.

Reads GRADER, ENABLE_CTC, ENABLE_RHYTHM and ENABLE_TONE from the environment and
provides layers_for(target, mode), which says which grading layers run for an
attempt.

Owner: B. Spec: docs/contracts/backend-interfaces.md, section 4.
"""

import os
from typing import Literal

GRADERS = ("mock", "real")


def grader() -> Literal["mock", "real"]:
    value = os.environ.get("GRADER", "real")
    if value == "mock":
        return "mock"
    if value == "real":
        return "real"
    raise ValueError(f"GRADER must be one of {GRADERS}, got {value!r}")
