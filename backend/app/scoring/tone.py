"""Lexical tone score for Word practice.

Provides score_tones: compares the pitch contour inside each syllable with the
four standard tone shapes and returns the expected tone, the heard tone and a
score. Never used on sung lines.

Owner: D. Spec: docs/contracts/scoring.md.
"""

from __future__ import annotations

import math

import numpy as np

from app.mandarin import sandhi_tones
from app.schemas import Audio, Span, Syllable, ToneGrade
from app.scoring.pitch import FRAME_MS, pitch_track

# Tone shapes on the five-level scale, sampled at five points across the syllable.
TONE_SHAPES = {
    1: [5, 5, 5, 5, 5],          # 55: high and level
    2: [3, 3.5, 4, 4.5, 5],      # 35: rising
    3: [2, 1.5, 1, 2.5, 4],      # 214: dipping, when the syllable ends the word
    4: [5, 4, 3, 2, 1],          # 51: falling
}
HALF_THIRD = [2, 1.75, 1.5, 1.25, 1]  # 21: a third tone inside a word only falls

# Starting values, to tune on our own recordings (scoring.md, tone section).
SEMITONES_PER_LEVEL = 2.5    # one step of the five-level scale
MIN_STRETCH, MAX_STRETCH = 0.5, 2.0  # how far a tone shape may scale to fit a speaker's range
SCORE_SCALE = 6.0            # semitones of distance at which the score falls to 37
WRONG_TONE_MAX = 60          # cap when another tone shape fits better
MIN_VOICED_MS = 50           # less voiced audio than this: no tone is measured
EDGE_TRIM = 0.1              # ignore the first and last tenth of each syllable


def score_tones(audio: Audio, expected: list[Syllable], spans: list[Span | None] | None) -> list[ToneGrade | None]:
    """Grade the tone of each expected syllable in a spoken word.

    spans gives each syllable's place in the recording. spans=None is allowed
    only for a one-syllable word; the whole voiced part of the recording is used.

    Returns one entry per expected syllable: None when its tone is not scored
    (the neutral tone), or a ToneGrade whose heard and score are None when no
    clear pitch was found.
    """
    if spans is None:
        if len(expected) != 1:
            raise ValueError("spans can be omitted only for a one-syllable word")
    elif len(spans) != len(expected):
        raise ValueError("spans must have one entry per expected syllable")

    times_ms, semitones = pitch_track(audio.samples, audio.sample_rate)
    if spans is None:
        spans = [_voiced_span(times_ms, semitones)]

    targets = sandhi_tones(expected)
    shape_only = len(expected) == 1
    grades: list[ToneGrade | None] = []
    for position, (target, span) in enumerate(zip(targets, spans)):
        if target is None:
            grades.append(None)
            continue
        contour = _contour(times_ms, semitones, span)
        if contour is None:
            grades.append(ToneGrade(expected=target, heard=None, score=None))
            continue

        word_final = position == len(expected) - 1
        templates = {tone: _template(tone, word_final) for tone in TONE_SHAPES}
        if shape_only:
            # One syllable has nothing to compare its height against: compare shape only.
            contour = contour - contour.mean()
            templates = {tone: t - t.mean() for tone, t in templates.items()}
        distances = {tone: _distance(contour, t) for tone, t in templates.items()}

        heard = min(distances, key=distances.get)
        score = round(100 * math.exp(-distances[target] / SCORE_SCALE))
        if heard != target:
            score = min(score, WRONG_TONE_MAX)
        grades.append(ToneGrade(expected=target, heard=heard, score=score))
    return grades


def _distance(contour: np.ndarray, template: np.ndarray) -> float:
    """RMS gap in semitones after stretching the template to the speaker's pitch range.

    People move their pitch by different amounts, so the template may be scaled
    by between MIN_STRETCH and MAX_STRETCH before comparing. A level contour is
    then closest to the level first-tone shape, whatever its height.
    """
    energy = float(np.dot(template, template))
    stretch = 1.0 if energy == 0 else float(np.clip(np.dot(contour, template) / energy, MIN_STRETCH, MAX_STRETCH))
    return float(np.sqrt(np.mean((contour - stretch * template) ** 2)))


def _template(tone: int, word_final: bool) -> np.ndarray:
    """A tone shape in semitones relative to the middle of the speaker's range."""
    levels = HALF_THIRD if tone == 3 and not word_final else TONE_SHAPES[tone]
    return (np.array(levels, dtype=float) - 3) * SEMITONES_PER_LEVEL


def _voiced_span(times_ms: np.ndarray, semitones: np.ndarray) -> Span | None:
    """From the first to the last voiced frame of the recording."""
    voiced = times_ms[~np.isnan(semitones)]
    if voiced.size == 0:
        return None
    return Span(start_ms=int(voiced[0]), end_ms=int(voiced[-1]) + FRAME_MS, confidence=1.0)


def _contour(times_ms: np.ndarray, semitones: np.ndarray, span: Span | None) -> np.ndarray | None:
    """The syllable's pitch at five evenly spaced points, or None if too little is voiced."""
    if span is None:
        return None
    trim = (span.end_ms - span.start_ms) * EDGE_TRIM
    inside = (times_ms >= span.start_ms + trim) & (times_ms <= span.end_ms - trim)
    voiced = inside & ~np.isnan(semitones)
    if voiced.sum() * FRAME_MS < MIN_VOICED_MS:
        return None
    t, s = times_ms[voiced], semitones[voiced]
    return np.interp(np.linspace(t[0], t[-1], len(TONE_SHAPES[1])), t, s)
