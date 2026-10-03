"""Whisper base, step 1: speech to text.

Provides transcribe: runs faster-whisper on a recording and returns a Transcript
(the Hanzi text, its syllables with no tone or times, and a no_speech flag). The
model is loaded once and kept in memory.

Owner: B. Spec: docs/contracts/backend-interfaces.md, section 3.
"""
