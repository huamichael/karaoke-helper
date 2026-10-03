"""Tests for the scoring logic of the isolated-word experiment, pipeline/whisper_words.py.

Owner: B.
"""

from pathlib import Path

import pytest

from app import mandarin
from app.schemas import Syllable
from pipeline import whisper_words as ww

SOUNDS = {"是": ("sh", "i"), "事": ("sh", "i"), "四": ("s", "i"), "十": ("sh", "i")}


def fake_to_syllables(text: str, overrides=None) -> list[Syllable]:
    return [Syllable(hanzi=ch, pinyin="x", pinyin_numeric="x1", initial=SOUNDS[ch][0], final=SOUNDS[ch][1],
                     tone=None, start_ms=None, end_ms=None) for ch in text]


def not_implemented(text: str, overrides=None):
    raise NotImplementedError


@pytest.mark.parametrize(("name", "expected"), [
    ("我.wav", "我"), ("老虎__michael.m4a", "老虎"), ("跑得快__tts.aiff", "跑得快"),
])
def test_expected_word_comes_from_file_name(name, expected):
    assert ww.expected_of(Path("recordings") / name) == expected


@pytest.mark.parametrize(("expected", "heard", "outcome"), [
    ("是", "是", "exact"),
    ("是", "", "empty"),
    ("是", "事", "same_sound"),
    ("是", "四", "other"),
    ("是", "是是", "other"),
    ("是十", "事是", "same_sound"),
])
def test_classify_with_working_to_syllables(monkeypatch, expected, heard, outcome):
    monkeypatch.setattr(mandarin, "to_syllables", fake_to_syllables)
    assert ww.classify(expected, heard) == outcome


def test_homophones_count_as_other_until_to_syllables_exists(monkeypatch):
    monkeypatch.setattr(mandarin, "to_syllables", not_implemented)
    assert ww.classify("是", "事") == "other"
    assert ww.classify("是", "是") == "exact"
    assert ww.classify("是", "") == "empty"


def test_tally_lists_every_outcome_in_order():
    assert ww.tally(["exact", "empty", "exact"]) == {"exact": 2, "same_sound": 0, "other": 0, "empty": 1}
    assert ww.tally([]) == {"exact": 0, "same_sound": 0, "other": 0, "empty": 0}


def test_default_word_list():
    assert len(ww.WORDS) == 20
    assert len(set(ww.WORDS)) == 20
    assert sum(len(w) == 1 for w in ww.WORDS) == 10
