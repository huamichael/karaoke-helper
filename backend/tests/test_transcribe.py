"""Tests for transcribe in app/scoring/transcribe.py.

A fake model checks the arguments Whisper receives and how its text is cleaned.
The real model runs only with RUN_WHISPER=1, on Mandarin made by macOS `say`.

Owner: B.
"""

import os
import shutil
import subprocess
import time
from types import SimpleNamespace

import numpy as np
import pytest

from app import config, mandarin
from app.audio import load_audio
from app.schemas import Audio, Syllable
from app.scoring import transcribe as tr

AUDIO = Audio(samples=np.zeros(16000, dtype=np.float32), sample_rate=16000, trim_offset_ms=0)


class FakeModel:
    def __init__(self, *texts: str):
        self.texts = texts
        self.calls: list[tuple[np.ndarray, dict]] = []

    def transcribe(self, samples, **kwargs):
        self.calls.append((samples, kwargs))
        return iter(SimpleNamespace(text=t) for t in self.texts), None


def fake_to_syllables(text: str, overrides=None) -> list[Syllable]:
    return [Syllable(hanzi=ch, pinyin="x", pinyin_numeric="x1", initial="x", final="i", tone=1,
                     start_ms=0, end_ms=10) for ch in text]


@pytest.fixture
def fake(monkeypatch):
    def install(*texts: str) -> FakeModel:
        model = FakeModel(*texts)
        monkeypatch.setenv("WHISPER_ENGINE", "faster")
        monkeypatch.setattr(tr, "load_model", lambda: model)
        monkeypatch.setattr(tr, "_faster_suppress", lambda: (-1, 11, 12))
        monkeypatch.setattr(mandarin, "to_syllables", fake_to_syllables)
        return model
    return install


def test_whisper_called_with_spec_arguments(fake, monkeypatch):
    monkeypatch.delenv("WHISPER_VAD", raising=False)
    model = fake("我想和李一起")
    tr.transcribe(AUDIO)
    samples, kwargs = model.calls[0]
    assert samples is AUDIO.samples
    assert kwargs == {"language": "zh", "beam_size": 5, "temperature": 0.0,
                      "condition_on_previous_text": False, "vad_filter": True,
                      "suppress_tokens": [-1, 11, 12]}


def test_vad_can_be_switched_off(fake, monkeypatch):
    monkeypatch.setenv("WHISPER_VAD", "0")
    model = fake("我")
    tr.transcribe(AUDIO)
    assert model.calls[0][1]["vad_filter"] is False


def test_segments_joined_and_non_hanzi_removed(fake):
    fake("我想，", " 和李一起。", "Thank you!")
    t = tr.transcribe(AUDIO)
    assert t.text == "我想和李一起"
    assert [s.hanzi for s in t.syllables] == list("我想和李一起")
    assert t.no_speech is False


def test_tone_and_times_are_cleared(fake):
    fake("你")
    t = tr.transcribe(AUDIO)
    assert len(t.syllables) == 1
    assert all(s.tone is None and s.start_ms is None and s.end_ms is None for s in t.syllables)


def test_traditional_characters_kept(fake):
    fake("我們")
    assert tr.transcribe(AUDIO).text == "我們"


@pytest.mark.parametrize("texts", [(), ("",), ("Thank you.",), ("...", " ")])
def test_nothing_usable_is_no_speech(fake, texts):
    fake(*texts)
    t = tr.transcribe(AUDIO)
    assert (t.text, t.syllables, t.no_speech) == ("", [], True)


def test_model_loaded_once_with_configured_name(monkeypatch):
    built = []
    monkeypatch.setenv("WHISPER_ENGINE", "faster")
    monkeypatch.setattr(tr, "WhisperModel", lambda name, **kw: built.append((name, kw)) or object())
    monkeypatch.setenv("WHISPER_MODEL", "medium")
    monkeypatch.setattr(tr.os, "cpu_count", lambda: 11)
    tr.load_model.cache_clear()
    try:
        assert tr.load_model() is tr.load_model()
        assert built == [("medium", {"device": "cpu", "compute_type": "int8", "cpu_threads": 11})]
    finally:
        tr.load_model.cache_clear()


# --- engine switch ----------------------------------------------------------------


def test_default_engine_is_mlx_on_mac(monkeypatch):
    monkeypatch.delenv("WHISPER_ENGINE", raising=False)
    monkeypatch.setattr(config.sys, "platform", "darwin")
    assert config.whisper_engine() == "mlx"


def test_default_engine_is_faster_off_mac(monkeypatch):
    monkeypatch.delenv("WHISPER_ENGINE", raising=False)
    monkeypatch.setattr(config.sys, "platform", "linux")
    assert config.whisper_engine() == "faster"


def test_mlx_rejected_off_mac(monkeypatch):
    monkeypatch.setenv("WHISPER_ENGINE", "mlx")
    monkeypatch.setattr(config.sys, "platform", "linux")
    with pytest.raises(ValueError, match="macOS"):
        config.whisper_engine()


def test_bad_whisper_engine_rejected(monkeypatch):
    monkeypatch.setenv("WHISPER_ENGINE", "cuda")
    with pytest.raises(ValueError, match="WHISPER_ENGINE"):
        config.whisper_engine()


@pytest.mark.parametrize(("name", "repo"), [
    ("large-v3-turbo", "mlx-community/whisper-large-v3-turbo"),
    ("turbo", "mlx-community/whisper-large-v3-turbo"),
    ("medium", "mlx-community/whisper-medium-mlx"),
    ("mlx-community/custom", "mlx-community/custom"),
])
def test_mlx_repo_mapping(name, repo):
    assert tr.mlx_repo(name) == repo


def test_unknown_mlx_short_name_rejected():
    with pytest.raises(ValueError, match="unknown WHISPER_MODEL"):
        tr.mlx_repo("mystery")


def test_mlx_called_with_spec_arguments(monkeypatch):
    monkeypatch.setenv("WHISPER_ENGINE", "mlx")
    monkeypatch.setattr(config.sys, "platform", "darwin")
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    monkeypatch.setattr(mandarin, "to_syllables", fake_to_syllables)
    calls = []

    def fake_transcribe(samples, **kwargs):
        calls.append((samples, kwargs))
        return {"text": "我想，和你一起。Thank you"}

    monkeypatch.setattr(tr, "_mlx", lambda: (SimpleNamespace(transcribe=fake_transcribe), None))
    monkeypatch.setattr(tr, "_mlx_suppress", lambda: (-1, 21))
    t = tr.transcribe(AUDIO)
    samples, kwargs = calls[0]
    assert samples is AUDIO.samples
    assert kwargs == {
        "path_or_hf_repo": "mlx-community/whisper-large-v3-turbo",
        "language": "zh",
        "temperature": 0.0,
        "condition_on_previous_text": False,
        "verbose": None,
        "suppress_tokens": [-1, 21],
    }
    assert "beam_size" not in kwargs
    assert "vad_filter" not in kwargs
    assert "initial_prompt" not in kwargs
    assert t.text == "我想和你一起"
    assert t.no_speech is False


def test_mlx_no_speech_and_no_vad_kwarg(monkeypatch):
    monkeypatch.setenv("WHISPER_ENGINE", "mlx")
    monkeypatch.setattr(config.sys, "platform", "darwin")
    monkeypatch.setattr(mandarin, "to_syllables", fake_to_syllables)
    calls = []
    monkeypatch.setattr(tr, "_mlx", lambda: (SimpleNamespace(
        transcribe=lambda samples, **kwargs: calls.append(kwargs) or {"text": ""}), None))
    monkeypatch.setattr(tr, "_mlx_suppress", lambda: (-1,))
    t = tr.transcribe(AUDIO)
    assert t.no_speech is True
    assert "vad_filter" not in calls[0]


def test_mlx_model_loaded_once(monkeypatch):
    built = []
    monkeypatch.setenv("WHISPER_ENGINE", "mlx")
    monkeypatch.setattr(config.sys, "platform", "darwin")
    monkeypatch.setenv("WHISPER_MODEL", "medium")
    holder = SimpleNamespace(get_model=lambda repo, dtype: built.append((repo, dtype)) or object())
    monkeypatch.setattr(tr, "_mlx", lambda: (None, holder))
    monkeypatch.setattr(tr, "_mlx_dtype", lambda: "f16")
    suppress = []
    monkeypatch.setattr(tr, "_mlx_suppress", lambda: suppress.append("mlx") or (-1,))
    tr.load_mlx_model.cache_clear()
    try:
        assert tr.load_mlx_model() is tr.load_mlx_model()
        assert built == [("mlx-community/whisper-medium-mlx", "f16")]
        tr.warmup()
        assert built == [("mlx-community/whisper-medium-mlx", "f16")]
        assert suppress == ["mlx"]
    finally:
        tr.load_mlx_model.cache_clear()


def test_warmup_loads_faster_when_selected(monkeypatch):
    calls = []
    monkeypatch.setenv("WHISPER_ENGINE", "faster")
    monkeypatch.setattr(tr, "load_model", lambda: calls.append("faster"))
    monkeypatch.setattr(tr, "load_mlx_model", lambda: calls.append("mlx"))
    monkeypatch.setattr(tr, "_faster_suppress", lambda: calls.append("faster suppress") or (-1,))
    monkeypatch.setattr(tr, "_mlx_suppress", lambda: calls.append("mlx suppress") or (-1,))
    tr.warmup()
    assert calls == ["faster", "faster suppress"]


# --- Latin tokens are suppressed ------------------------------------------------------

VOCAB = {0: "好", 1: "How", 2: " how", 3: "，", 4: "é", 5: "OK", 6: "123", 7: "Hello"}


def test_latin_tokens_are_the_ones_with_latin_letters_below_eot():
    assert tr.latin_tokens(lambda ids: VOCAB[ids[0]], eot=7) == (1, 2, 5)


def test_latin_tokens_empty_vocabulary():
    assert tr.latin_tokens(lambda ids: VOCAB[ids[0]], eot=0) == ()


def test_faster_suppress_list_built_once_from_model_tokenizer(monkeypatch):
    decoded = []
    hf = SimpleNamespace(decode=lambda ids: decoded.append(ids[0]) or VOCAB[ids[0]],
                         token_to_id=lambda name: {"<|endoftext|>": 7}[name])
    monkeypatch.setattr(tr, "load_model", lambda: SimpleNamespace(hf_tokenizer=hf))
    tr._faster_suppress.cache_clear()
    try:
        assert tr._faster_suppress() == (-1, 1, 2, 5)
        assert tr._faster_suppress() == (-1, 1, 2, 5)
        assert decoded == list(range(7))
    finally:
        tr._faster_suppress.cache_clear()


def test_mlx_suppress_list_keeps_whisper_symbols_and_uses_the_model_language_count(monkeypatch):
    mt = pytest.importorskip("mlx_whisper.tokenizer")
    asked = []

    def get_tokenizer(multilingual, *, num_languages, language, task):
        asked.append((multilingual, num_languages, language, task))
        return SimpleNamespace(decode=lambda ids: VOCAB[ids[0]], eot=7)

    monkeypatch.setattr(mt, "get_tokenizer", get_tokenizer)
    monkeypatch.setattr(tr, "load_mlx_model", lambda: SimpleNamespace(num_languages=100))
    tr._mlx_suppress.cache_clear()
    try:
        assert tr._mlx_suppress() == (-1, 1, 2, 5)
        assert asked == [(True, 100, "zh", "transcribe")]
    finally:
        tr._mlx_suppress.cache_clear()


# --- real model, opt-in -----------------------------------------------------------

needs_whisper = pytest.mark.skipif(
    os.environ.get("RUN_WHISPER") != "1" or not shutil.which("say"),
    reason="set RUN_WHISPER=1 on a Mac with the Tingting voice to run the real model",
)


def tts(text: str, tmp_path) -> bytes:
    out = tmp_path / "tts.aiff"
    subprocess.run(["say", "-v", "Tingting", "-o", str(out), text], check=True)
    return out.read_bytes()


@needs_whisper
def test_real_whisper_on_synthetic_mandarin(monkeypatch, tmp_path):
    monkeypatch.setenv("WHISPER_ENGINE", "faster")
    monkeypatch.setattr(mandarin, "to_syllables", fake_to_syllables)
    audio = load_audio(tts("我想和你一起", tmp_path))
    tr.transcribe(audio)  # warm-up: loads the model
    start = time.perf_counter()
    t = tr.transcribe(audio)
    elapsed = time.perf_counter() - start
    print(f"\nwhisper heard {t.text!r} in {elapsed:.2f}s ({len(audio.samples) / 16000:.2f}s of audio)")
    assert not t.no_speech
    assert sum(ch in t.text for ch in "我想和你一起") >= 5


@needs_whisper
def test_real_whisper_on_silence_is_no_speech(monkeypatch):
    monkeypatch.setenv("WHISPER_ENGINE", "faster")
    monkeypatch.setattr(mandarin, "to_syllables", fake_to_syllables)
    t = tr.transcribe(Audio(samples=np.zeros(32000, dtype=np.float32), sample_rate=16000, trim_offset_ms=0))
    assert t.no_speech, f"Whisper invented {t.text!r} on silence"


needs_mlx = pytest.mark.skipif(
    os.environ.get("RUN_WHISPER") != "1" or not shutil.which("say"),
    reason="set RUN_WHISPER=1 on a Mac to time mlx-whisper",
)


@needs_mlx
def test_real_mlx_on_synthetic_mandarin(monkeypatch, tmp_path):
    pytest.importorskip("mlx_whisper")
    monkeypatch.setenv("WHISPER_ENGINE", "mlx")
    monkeypatch.setattr(mandarin, "to_syllables", fake_to_syllables)
    audio = load_audio(tts("我想和你一起", tmp_path))
    tr.transcribe(audio)
    start = time.perf_counter()
    t = tr.transcribe(audio)
    elapsed = time.perf_counter() - start
    print(f"\nmlx heard {t.text!r} in {elapsed:.2f}s ({len(audio.samples) / 16000:.2f}s of audio)")
    assert not t.no_speech
    assert sum(ch in t.text for ch in "我想和你一起") >= 5


@needs_mlx
@pytest.mark.parametrize("engine", ["mlx", "faster"])
def test_real_whisper_writes_hanzi_for_an_english_sounding_syllable(monkeypatch, tmp_path, engine):
    if engine == "mlx":
        pytest.importorskip("mlx_whisper")
    monkeypatch.setenv("WHISPER_ENGINE", engine)
    monkeypatch.setattr(mandarin, "to_syllables", fake_to_syllables)
    out = tmp_path / "how.aiff"
    subprocess.run(["say", "-v", "Samantha", "-o", str(out), "How"], check=True)
    t = tr.transcribe(load_audio(out.read_bytes()))
    print(f"\n{engine} heard {t.text!r} for English 'How'")
    assert not t.no_speech
