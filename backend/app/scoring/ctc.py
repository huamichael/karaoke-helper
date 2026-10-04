"""Local MMS forced alignment and component likelihood scoring (owner C).

Scoring follows docs/contracts/scoring.md. Imports and model downloads are
lazy, so disabled layers and mock grading do not need PyTorch. Audio samples
must not be changed between align() and score_sounds().
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from math import prod, tanh
import re
from threading import RLock
import weakref

import numpy as np

from app.schemas import Audio, Part, SoundScore, Span, Syllable
from app.scoring.confusions import final_partners, initial_partners

# Experimental starting parameters, pending checkpoint B. A winning confused
# variant is capped at 60 as required by scoring.md; no calibration is claimed.
MIN_SPAN_MS = 40
MIN_CONFIDENCE = 0.1
MARGIN_MS = 100
MARGIN_SCALE = 0.25
TIE_SCORE = 70
WRONG_MAX = 60
FRAME_MS = 20
SAMPLE_RATE = 16_000
CACHE_SIZE = 8


@dataclass(frozen=True)
class _Emission:
    log_probs: np.ndarray
    dictionary: dict[str, int]
    frame_ms: float
    blank: int = 0


class _NoPath(Exception):
    """The cropped emission cannot accommodate any component candidate."""


_cache: OrderedDict[int, tuple[weakref.ReferenceType[Audio], _Emission]] = OrderedDict()
_lock = RLock()


@lru_cache(maxsize=1)
def _runtime():
    """Load once, retaining CPU weights in the native/Docker model cache."""
    try:
        import torch
        import torchaudio
    except (ImportError, OSError) as exc:
        raise RuntimeError("CTC needs pinned torch/torchaudio dependencies; run uv sync") from exc
    if not callable(getattr(torchaudio.functional, "forced_align", None)):
        raise RuntimeError("This torchaudio build has no forced_align; verify pinned 2.11")
    bundle = torchaudio.pipelines.MMS_FA
    model = bundle.get_model(with_star=False).cpu().eval()
    acoustic_model = getattr(model, "model", model)
    stride = prod(layer.conv.stride[0] for layer in acoustic_model.feature_extractor.conv_layers)
    frame_ms = stride * 1000 / bundle.sample_rate
    if bundle.sample_rate != SAMPLE_RATE or frame_ms != FRAME_MS:
        raise RuntimeError(f"Unexpected MMS frame geometry: {bundle.sample_rate} Hz, {frame_ms} ms")
    return torch, torchaudio, model, bundle.get_dict(star=None), frame_ms


def _infer(audio: Audio) -> _Emission:
    torch, _, model, dictionary, frame_ms = _runtime()
    with torch.inference_mode():
        output, _ = model(torch.from_numpy(audio.samples.copy()).unsqueeze(0))
        log_probs = output.log_softmax(-1)[0].cpu().numpy()
    return _Emission(log_probs, dictionary, frame_ms)


def _emissions(audio: Audio) -> _Emission:
    """Identity cache with weak references, bounded memory, and no id reuse."""
    key = id(audio)
    with _lock:
        cached = _cache.get(key)
        if cached is not None and cached[0]() is audio:
            _cache.move_to_end(key)
            return cached[1]
        emission = _infer(audio)

        def release(reference):
            with _lock:
                current = _cache.get(key)
                if current is not None and current[0] is reference:
                    del _cache[key]

        _cache[key] = (weakref.ref(audio, release), emission)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
        return emission


def _validate_audio(audio: Audio) -> None:
    if audio.sample_rate != SAMPLE_RATE:
        raise ValueError("CTC requires 16000 Hz audio")
    if audio.samples.ndim != 1 or audio.samples.dtype != np.float32:
        raise ValueError("CTC requires mono float32 samples")
    if not np.isfinite(audio.samples).all():
        raise ValueError("CTC samples must be finite")


def _letters(syllable: Syllable) -> str:
    numeric = syllable.pinyin_numeric.lower()
    if not re.fullmatch(r"[a-z]+[1-5]", numeric):
        raise ValueError(f"Invalid pinyin_numeric: {syllable.pinyin_numeric!r}")
    return numeric[:-1]


def _variant(syllable: Syllable, *, initial: str | None = None, final: str | None = None) -> str:
    """Keep standard spelling for initials; normalize strict finals ourselves.

    Acoustic candidates are not new Hanzi/Syllable records. Full strict finals
    contract after consonants; vowel-only forms use standard y/w spelling.
    """
    letters = _letters(syllable)
    if final is None:
        return (initial or "") + letters[len(syllable.initial):]
    ini = syllable.initial if initial is None else initial
    if ini:
        spelling = {"iou": "iu", "uei": "ui", "uen": "un"}.get(final, final)
        if ini in ("j", "q", "x"):
            spelling = spelling.replace("v", "u")
        return ini + spelling
    if final.startswith("v"):
        return "yu" + final[1:]
    if final.startswith("i"):
        return "y" + (final if final in ("i", "in", "ing") else final[1:])
    if final.startswith("u"):
        return "wu" if final == "u" else "w" + final[1:]
    return final


def _tokens(letters: str, emission: _Emission) -> list[int]:
    try:
        return [emission.dictionary[letter] for letter in letters]
    except KeyError as exc:
        raise ValueError(f"MMS vocabulary does not support {exc.args[0]!r}") from exc


def _minimum_frames(targets: list[int]) -> int:
    return len(targets) + sum(a == b for a, b in zip(targets, targets[1:]))


def _forced_path(emission: _Emission, targets: list[int]) -> np.ndarray:
    torch, torchaudio, _, _, _ = _runtime()
    path, _ = torchaudio.functional.forced_align(
        torch.from_numpy(emission.log_probs).unsqueeze(0),
        torch.tensor([targets], dtype=torch.int64), blank=emission.blank,
    )
    return path[0].cpu().numpy()


def align(audio: Audio, expected: list[Syllable]) -> list[Span | None]:
    """Return syllable spans in trimmed sample time, ignoring lexical tones."""
    if not expected:
        return []
    _validate_audio(audio)
    duration_ms = len(audio.samples) * 1000 / audio.sample_rate
    if duration_ms < MIN_SPAN_MS or not np.any(audio.samples):
        return [None] * len(expected)
    emission = _emissions(audio)
    spellings = [_letters(s) for s in expected]
    targets = _tokens("".join(spellings), emission)
    if len(emission.log_probs) < _minimum_frames(targets):
        return [None] * len(expected)
    path = _forced_path(emission, targets)
    # A blank splits repeated letters; a nonblank change starts another token.
    runs: list[tuple[int, int, int]] = []
    for frame, token in enumerate(path):
        if token == emission.blank:
            continue
        if frame and token == path[frame - 1]:
            start, _, value = runs[-1]
            runs[-1] = (start, frame + 1, value)
        else:
            runs.append((frame, frame + 1, int(token)))
    if [value for _, _, value in runs] != targets:
        raise RuntimeError("CTC alignment did not recover the full target token sequence")
    result: list[Span | None] = []
    position = 0
    for spelling in spellings:
        group = runs[position:position + len(spelling)]
        position += len(spelling)
        start_ms = round(group[0][0] * emission.frame_ms)
        end_ms = min(round(group[-1][1] * emission.frame_ms), int(duration_ms))
        probabilities = np.concatenate([
            np.exp(emission.log_probs[start:end, token]) for start, end, token in group
        ])
        confidence = float(np.clip(probabilities.mean(), 0, 1))
        result.append(
            None if end_ms - start_ms < MIN_SPAN_MS or confidence < MIN_CONFIDENCE
            else Span(start_ms=start_ms, end_ms=end_ms, confidence=confidence)
        )
    return result


def _best_path_mean(log_probs: np.ndarray, targets: list[int], blank: int) -> float:
    """Viterbi CTC likelihood in a fixed window, including blanks (no decode)."""
    frames = len(log_probs)
    if not targets or frames < _minimum_frames(targets):
        return float("-inf")
    states = np.full(2 * len(targets) + 1, blank, dtype=np.int64)
    states[1::2] = targets
    previous = np.full(len(states), -np.inf)
    previous[:2] = log_probs[0, states[:2]]
    skip = np.zeros(len(states), dtype=bool)
    skip[2:] = (states[2:] != blank) & (states[2:] != states[:-2])
    for row in log_probs[1:]:
        one = np.r_[-np.inf, previous[:-1]]
        two = np.r_[-np.inf, -np.inf, previous[:-2]]
        previous = np.maximum(np.maximum(previous, one), np.where(skip, two, -np.inf)) + row[states]
    return float(max(previous[-2:]) / frames)


def _margin_score(expected: float, other: float) -> int:
    if not np.isfinite(expected):
        return 40
    if not np.isfinite(other):
        return 100
    margin = expected - other
    score = round(TIE_SCORE + 30 * tanh(margin / MARGIN_SCALE))
    return min(WRONG_MAX if margin < 0 else 100, max(0, score))


def _component(syllable: Syllable, kind: str, span: Span, emission: _Emission, window: np.ndarray) -> Part | None:
    sound = getattr(syllable, kind)
    if kind == "initial" and not sound:
        return None
    partners = initial_partners(sound) if kind == "initial" else final_partners(sound)
    if not partners:
        return Part(expected=sound, heard=sound, score=round(100 * span.confidence))
    candidates = [(sound, _letters(syllable))] + [
        (partner, _variant(syllable, **{kind: partner})) for partner in partners
    ]
    likelihoods = [_best_path_mean(window, _tokens(letters, emission), emission.blank) for _, letters in candidates]
    if not any(np.isfinite(value) for value in likelihoods):
        raise _NoPath
    best = max(range(len(candidates)), key=lambda i: likelihoods[i])
    return Part(expected=sound, heard=candidates[best][0], score=_margin_score(likelihoods[0], max(likelihoods[1:])))


def score_sounds(audio: Audio, expected: list[Syllable], spans: list[Span | None]) -> list[SoundScore | None]:
    """Compare initial/final partners using the emissions cached by align()."""
    if len(spans) != len(expected):
        raise ValueError("spans must have one entry per expected syllable")
    if not expected or all(span is None for span in spans):
        return [None] * len(expected)
    _validate_audio(audio)
    emission = _emissions(audio)
    result: list[SoundScore | None] = []
    for syllable, span in zip(expected, spans):
        if span is None:
            result.append(None)
            continue
        start = max(0, int(np.floor((span.start_ms - MARGIN_MS) / emission.frame_ms)))
        end = min(len(emission.log_probs), int(np.ceil((span.end_ms + MARGIN_MS) / emission.frame_ms)))
        if start >= end or span.start_ms < 0 or span.end_ms <= span.start_ms:
            result.append(None)
            continue
        window = emission.log_probs[start:end]
        try:
            initial = _component(syllable, "initial", span, emission, window)
            final = _component(syllable, "final", span, emission, window)
        except _NoPath:
            result.append(None)
        else:
            result.append(SoundScore(initial=initial, final=final))
    return result
