"""Checkpoint B script. Run by hand; pytest does not collect it.

Compares the Whisper base and the CTC layer on the fixture recordings: errors
caught and correct syllables wrongly flagged, per layer. Also writes the audio
cut at each span, for listening.

Owner: C. Spec: docs/tasks/backend-ctc-rhythm.md.
"""
