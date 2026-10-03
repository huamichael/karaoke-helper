"""Mandarin text handling: the only place Hanzi becomes Syllable records.

Provides to_syllables (text to syllables, with optional reading overrides),
segment_words (split a line into words) and sandhi_tones (the tones a word is
expected to be spoken with). Nothing else in the project calls pypinyin.

Owner: D. Spec: docs/contracts/data-model.md, section 2.
"""

from __future__ import annotations

from app.schemas import Syllable


def to_syllables(text: str, overrides: dict[int, str] | None = None) -> list[Syllable]:
    raise NotImplementedError


def segment_words(text: str) -> list[str]:
    raise NotImplementedError


def sandhi_tones(syllables: list[Syllable]) -> list[int | None]:
    raise NotImplementedError
