"""Whisper base, step 1: speech to text.

Provides transcribe: runs Whisper on a recording and returns a Transcript (the
Hanzi text, its syllables with no tone or times, and a no_speech flag). On macOS
the default engine is mlx-whisper; elsewhere, and in Docker, it is faster-whisper.
The chosen model is loaded once and kept in memory.

Owner: B. Spec: docs/contracts/backend-interfaces.md, section 3.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from functools import lru_cache

from faster_whisper import WhisperModel

from app import config, mandarin
from app.schemas import Audio, Transcript
from app.songs import is_hanzi

MLX_REPOS = {
    "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
    "turbo": "mlx-community/whisper-large-v3-turbo",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "tiny": "mlx-community/whisper-tiny-mlx",
}


def mlx_repo(name: str) -> str:
    if "/" in name:
        return name
    try:
        return MLX_REPOS[name]
    except KeyError:
        raise ValueError(
            f"unknown WHISPER_MODEL {name!r} for mlx; use a Hugging Face repo id"
        ) from None


def _mlx():
    try:
        import mlx_whisper
        from mlx_whisper.transcribe import ModelHolder
    except ImportError as e:
        raise ImportError(
            "mlx-whisper is required when WHISPER_ENGINE=mlx. On a Mac: uv sync"
        ) from e
    return mlx_whisper, ModelHolder


def _mlx_dtype():
    import mlx.core as mx
    return mx.float16


@lru_cache(maxsize=1)
def load_model() -> WhisperModel:
    # faster-whisper defaults to 4 threads; all cores cut large-v3-turbo from ~7.7 s to ~5 s per line on an M-series Mac.
    return WhisperModel(os.environ.get("WHISPER_MODEL", "large-v3-turbo"), device="cpu", compute_type="int8",
                        cpu_threads=os.cpu_count() or 0)


@lru_cache(maxsize=1)
def load_mlx_model():
    repo = mlx_repo(os.environ.get("WHISPER_MODEL", "large-v3-turbo"))
    _, holder = _mlx()
    return holder.get_model(repo, _mlx_dtype())


_LATIN = re.compile(r"[A-Za-z]")


def latin_tokens(decode: Callable[[list[int]], str], eot: int) -> tuple[int, ...]:
    """The text tokens (ids below eot) whose text contains a Latin letter.

    Whisper writes English for Mandarin that sounds like an English word ("How" for hào).
    Only Hanzi are kept, so that would read as no speech. Suppressing these tokens makes
    it write Hanzi instead. It says nothing about the expected lyric.
    """
    return tuple(i for i in range(eot) if _LATIN.search(decode([i])))


@lru_cache(maxsize=1)
def _mlx_suppress() -> tuple[int, ...]:
    from mlx_whisper.tokenizer import get_tokenizer
    tok = get_tokenizer(multilingual=True, num_languages=load_mlx_model().num_languages, language="zh", task="transcribe")
    return (-1, *latin_tokens(tok.decode, tok.eot))  # -1 keeps Whisper's own suppressed symbols


@lru_cache(maxsize=1)
def _faster_suppress() -> tuple[int, ...]:
    hf = load_model().hf_tokenizer
    return (-1, *latin_tokens(hf.decode, hf.token_to_id("<|endoftext|>")))


def warmup() -> None:
    if config.whisper_engine() == "mlx":
        load_mlx_model()
        _mlx_suppress()
    else:
        load_model()
        _faster_suppress()


def heard_text(audio: Audio) -> str:
    """The Hanzi Whisper hears, everything else removed."""
    raw = _heard_mlx(audio) if config.whisper_engine() == "mlx" else _heard_faster(audio)
    return "".join(ch for ch in raw if is_hanzi(ch))


def _heard_faster(audio: Audio) -> str:
    # Never pass the expected lyric as initial_prompt: it biases the transcript toward a pass.
    segments, _ = load_model().transcribe(
        audio.samples,
        language="zh",
        beam_size=5,
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=os.environ.get("WHISPER_VAD", "1") != "0",
        suppress_tokens=list(_faster_suppress()),
    )
    return "".join(segment.text for segment in segments)


def _heard_mlx(audio: Audio) -> str:
    # mlx-whisper 0.4.3 has no beam search and no vad_filter. Greedy + temperature 0 is its beam_size=5 stand-in.
    mlx, _ = _mlx()
    result = mlx.transcribe(
        audio.samples,
        path_or_hf_repo=mlx_repo(os.environ.get("WHISPER_MODEL", "large-v3-turbo")),
        language="zh",
        temperature=0.0,
        condition_on_previous_text=False,
        verbose=None,
        suppress_tokens=list(_mlx_suppress()),
    )
    return result.get("text", "")


def transcribe(audio: Audio) -> Transcript:
    text = heard_text(audio)
    syllables = [s.model_copy(update={"tone": None, "start_ms": None, "end_ms": None})
                 for s in mandarin.to_syllables(text)] if text else []
    return Transcript(text=text, syllables=syllables, no_speech=not text)
