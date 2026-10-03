"""The grading orchestrator.

Provides grade: runs the Whisper base, then whichever of the CTC, rhythm and tone
layers are switched on, and assembles one AttemptResult (syllable scores,
statuses, word roll-up, overall scores, feedback, next step). A layer that fails
is skipped, so the Whisper-base result is always returned.

Owner: B. Spec: docs/contracts/backend-interfaces.md, section 4; docs/contracts/scoring.md.
"""

from __future__ import annotations

from app.schemas import AttemptResult, Audio, Line


def grade(audio: Audio, line: Line, target: str, mode: str | None, word_index: int | None) -> AttemptResult:
    raise NotImplementedError
