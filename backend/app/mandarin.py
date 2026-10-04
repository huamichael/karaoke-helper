"""Mandarin text handling: the only place Hanzi becomes Syllable records.

Provides to_syllables (text to syllables, with optional reading overrides),
segment_words (split a line into words) and sandhi_tones (the tones a word is
expected to be spoken with). Nothing else in the project calls pypinyin.

Owner: D. Spec: docs/contracts/data-model.md, section 2.
"""

from __future__ import annotations

import logging
import re

import jieba
import zhconv
from pypinyin import Style, lazy_pinyin
from pypinyin.contrib.tone_convert import to_finals, to_initials, to_tone

from app.schemas import Syllable

# Hanzi: CJK unified ideographs (base block and extensions A to H),
# compatibility ideographs, and 〇. Everything else is dropped.
_HANZI = (
    "\u3007\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
    "\U00020000-\U0002ebef\U00030000-\U000323af"
)
_HANZI_RUN = re.compile(f"[{_HANZI}]+")
_NUMERIC = re.compile(r"[a-z]+[1-5]")

jieba.setLogLevel(logging.WARNING)


def to_syllables(text: str, overrides: dict[int, str] | None = None) -> list[Syllable]:
    """Convert text to one Syllable per Hanzi character, in order.

    Non-Hanzi characters (punctuation, spaces, Latin letters) produce nothing.
    Works for Simplified and Traditional characters. Times are None.

    overrides maps a character position in text (counting every character,
    spaces included, from 0) to a pinyin_numeric reading such as "di4". It
    replaces pypinyin's reading for songs that sing a character differently.

    Raises ValueError if an override does not point at a Hanzi character or is
    not a valid reading, or if a character has no known reading.
    """
    overrides = overrides or {}
    for position in overrides:
        if not 0 <= position < len(text) or not _HANZI_RUN.fullmatch(text[position]):
            raise ValueError(f"override position {position} is not a Hanzi character in {text!r}")

    syllables = []
    # Convert each run of consecutive Hanzi as a whole, so pypinyin can use the
    # surrounding characters to choose between readings (for example 一 in 一起).
    for run in _HANZI_RUN.finditer(text):
        readings = _readings(run.group())
        for offset, (hanzi, reading) in enumerate(zip(run.group(), readings)):
            reading = overrides.get(run.start() + offset, reading)
            syllables.append(_syllable(hanzi, reading))
    return syllables


def segment_words(text: str) -> list[str]:
    """Split a line into words. The words joined together equal the Hanzi of text.

    Non-Hanzi characters are dropped, and a word never spans a space or
    punctuation. jieba's dictionary is Simplified, so Traditional text is
    segmented through its Simplified form and mapped back character by character.
    """
    words = []
    for run in _HANZI_RUN.findall(text):
        simplified = zhconv.convert(run, "zh-cn")
        if len(simplified) != len(run):
            simplified = run  # conversion changed the length; segment as written
        position = 0
        for piece in jieba.cut(simplified, HMM=False):
            words.append(run[position : position + len(piece)])
            position += len(piece)
    return words


def sandhi_tones(syllables: list[Syllable]) -> list[int | None]:
    """The tone each syllable is expected to be spoken with, after tone sandhi.

    Applies, in order:
    - 一: second tone before a fourth or neutral tone, fourth tone before any
      other tone, first tone at the end or after 第. Neutral between two copies
      of the same character, as in 想一想.
    - 不: second tone before a fourth tone, otherwise fourth. Neutral between
      two copies of the same character, as in 好不好.
    - Third tone: in a run of third tones, all but the last become second tone.

    Returns None for the neutral tone, which is not scored.
    """
    hanzi = [s.hanzi for s in syllables]
    lexical = [s.tone for s in syllables]
    tones: list[int | None] = []
    for i, tone in enumerate(lexical):
        before = hanzi[i - 1] if i > 0 else None
        after = hanzi[i + 1] if i + 1 < len(hanzi) else None
        next_tone = lexical[i + 1] if after is not None else None
        if hanzi[i] in "一不" and before is not None and before == after:
            tone = 5
        elif hanzi[i] == "一":
            if after is None or before == "第":
                tone = 1
            else:
                tone = 2 if next_tone in (4, 5) else 4
        elif hanzi[i] == "不":
            tone = 2 if next_tone == 4 else 4
        tones.append(None if tone in (5, None) else tone)

    for i in range(len(tones) - 1):
        if tones[i] == 3 and tones[i + 1] == 3:
            tones[i] = 2
    return tones


def spell(initial: str, final: str, tone: int | None = None) -> str:
    """Pinyin for an initial and a strict final, as a learner reads it.

    ("", "uo") -> "wo", ("j", "v") -> "ju", ("n", "v") -> "nü", ("x", "in", 1) -> "xīn".
    With a tone (1-4) the vowel carries its mark; with none, or 5, there is no mark.
    Used to show a syllable that was heard, which may not be a word.
    """
    if initial:
        letters = initial + {"iou": "iu", "uei": "ui", "uen": "un"}.get(final, final)
        if initial in ("j", "q", "x"):
            letters = letters.replace("v", "u")
    elif final.startswith("v"):
        letters = "yu" + final[1:]
    elif final.startswith("i"):
        letters = "y" + (final if final in ("i", "in", "ing") else {"iou": "ou"}.get(final, final[1:]))
    elif final.startswith("u"):
        letters = "wu" if final == "u" else "w" + {"uei": "ei", "uen": "en"}.get(final, final[1:])
    else:
        letters = final
    if tone in (1, 2, 3, 4):
        return to_tone(f"{letters}{tone}")
    return letters.replace("v", "ü")


def _readings(run: str) -> list[str]:
    """pypinyin's pinyin_numeric reading for each character of a run of Hanzi."""
    readings = lazy_pinyin(run, style=Style.TONE3, neutral_tone_with_five=True)
    if len(readings) != len(run):
        # pypinyin returns characters it cannot read as one combined item, so
        # fall back to one character at a time to keep one reading per Hanzi.
        readings = [
            lazy_pinyin(hanzi, style=Style.TONE3, neutral_tone_with_five=True)[0]
            for hanzi in run
        ]
    return readings


def _syllable(hanzi: str, numeric: str) -> Syllable:
    """Build a Syllable from one character and its pinyin_numeric reading."""
    numeric = numeric.strip().lower().replace("ü", "v")
    if not _NUMERIC.fullmatch(numeric):
        raise ValueError(
            f"no valid reading for {hanzi!r}: got {numeric!r}. "
            "Give one as an override, for example 'hao3' or 'nv3'."
        )
    return Syllable(
        hanzi=hanzi,
        pinyin=to_tone(numeric),
        pinyin_numeric=numeric,
        initial=to_initials(numeric, strict=True),
        final=to_finals(numeric, strict=True),
        tone=int(numeric[-1]),
        start_ms=None,
        end_ms=None,
    )
