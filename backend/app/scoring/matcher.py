"""Whisper base, step 2: line up what was heard against what was expected.

Provides match (sequence-aligns the heard syllables to the expected ones and
returns one observed syllable, or None, per expected syllable) and
score_sounds_base (the 100 / 60 / 20 component scores for initials and finals).

Owner: B. Spec: docs/contracts/scoring.md.
"""
