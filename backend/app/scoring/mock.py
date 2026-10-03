"""Mock grader, selected with GRADER=mock.

Returns a valid, deterministic AttemptResult built from the expected line without
looking at the audio. It cycles through every status so the frontend can be built
before the real grader exists.

Owner: B. Spec: docs/tasks/backend-api-whisper.md.
"""
