"""The recording session: every test recording the team needs, in one place.

prompts.py makes a clip to copy for each item, and check_recordings.py checks
the recordings against this list. The guide for the people recording is
docs/recording-session.md.

File names: <item>__<variant>__<speaker>.wav
- Lines go in audio/, where <item> is a fixture line in lines/.
- Single words go in tone/, where <item> is the word's reading, such as xin1.
- <speaker> is the recorder's first name in lowercase ASCII letters.

Owner: D. Spec: docs/contracts/backend-interfaces.md, section 6.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SPEAKER = re.compile(r"[a-z]+")


@dataclass(frozen=True)
class Take:
    """One recording each speaker makes."""

    folder: str        # "audio" for lines, "tone" for single words
    item: str          # fixture line name, or the word's reading
    variant: str
    say: str           # Hanzi the prompt voice speaks (changed for errors and missing words)
    how: str           # instruction for the person recording


# Lines: (fixture name, song folder, line index in song.json, error, missing word).
# error is (variant, prompt text, instruction); missing is (variant, prompt text, instruction).
LINES = {
    "yueliang": (
        "月亮代表我的心", "yue-liang-dai-biao-wo-de-xin", 3,
        ("error-1-iang-ian", "月练代表我的心", "Sing it, but say 亮 liàng as liàn: drop the final \"ng\"."),
        ("missing-4", "月亮代表的心", "Sing it, but leave out 我 (wǒ), the fifth character."),
    ),
    "yijianmei": (
        "冷冷冰雪不能掩没", "yi-jian-mei", 5,
        ("error-2-ing-in", "冷冷宾雪不能掩没", "Sing it, but say 冰 bīng as bīn: drop the final \"g\"."),
        ("missing-4", "冷冷冰雪能掩没", "Sing it, but leave out 不 (bù), the fifth character."),
    ),
    "jasmine": (
        "好一朵美麗的茉莉花", "jasmine-flower", 0,
        ("error-4-l-n", "好一朵美腻的茉莉花", "Sing it, but say 麗 lì as nì: start with \"n\" instead of \"l\"."),
        ("missing-1", "好朵美麗的茉莉花", "Sing it, but leave out 一 (yī), the second character."),
    ),
}

# Single words for tone, said normally. reading -> Hanzi. Six per tone.
WORDS = {
    "xin1": "心", "xiang1": "香", "zhen1": "真", "jiang1": "將", "kua1": "誇", "ma1": "妈",
    "qing2": "情", "bai2": "白", "lai2": "來", "ren2": "人", "ma2": "麻",
    "wo3": "我", "ni3": "你", "you3": "有", "wen3": "吻", "ma3": "马",
    "ai4": "愛", "wen4": "問", "qu4": "去", "rang4": "讓", "ma4": "骂",
}

# Words also recorded with each wrong tone, to check that mistakes are caught.
WRONG_TONE_WORDS = ("xin1", "qing2", "wo3", "ai4")

TONE_SHAPE_WORDS = {1: "high and level", 2: "rising", 3: "dipping low, then rising", 4: "falling sharply"}


def takes() -> list[Take]:
    """Every recording one speaker makes, in session order."""
    result = []
    for name, (text, _, _, error, missing) in LINES.items():
        result.append(Take("audio", name, "correct", text, "Listen to the original, then sing the line back on your own, as written."))
        result.append(Take("audio", name, "spoken", text, "Say the line normally, without any melody."))
        result.append(Take("audio", name, error[0], error[1], error[2]))
        result.append(Take("audio", name, missing[0], missing[1], missing[2]))
    for reading, hanzi in WORDS.items():
        tone = int(reading[-1])
        result.append(Take("tone", reading, "correct", hanzi,
                           f"Say {hanzi} ({reading}) on its own, normally. Its tone is {TONE_SHAPE_WORDS[tone]}."))
    for reading in WRONG_TONE_WORDS:
        hanzi, right = WORDS[reading], int(reading[-1])
        for tone in (1, 2, 3, 4):
            if tone != right:
                result.append(Take("tone", reading, f"said-tone{tone}", hanzi,
                                   f"Say {hanzi} with the wrong tone: make it {TONE_SHAPE_WORDS[tone]}, like the prompt."))
    return result


def file_name(take: Take, speaker: str) -> str:
    return f"{take.item}__{take.variant}__{speaker}.wav"


def parse(name: str) -> tuple[str, str, str] | None:
    """(item, variant, speaker) from a recording's file name, without the extension."""
    parts = name.split("__")
    if len(parts) != 3 or not SPEAKER.fullmatch(parts[2]):
        return None
    return parts[0], parts[1], parts[2]
