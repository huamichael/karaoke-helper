"""The grading orchestrator.

Provides grade: runs the Whisper base, then whichever of the CTC, rhythm and tone
layers are switched on, and assembles one AttemptResult (syllable scores,
statuses, word roll-up, overall scores, feedback, next step). A layer that fails
is skipped, so the Whisper-base result is always returned.

Owner: B. Spec: docs/contracts/backend-interfaces.md, section 4; docs/contracts/scoring.md.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence

from app import config, songs
from app.schemas import (
    AttemptResult,
    Audio,
    Heard,
    Line,
    LineStep,
    Part,
    PracticeWordStep,
    RhythmResult,
    RhythmSyllable,
    Scores,
    SoundScore,
    Span,
    Status,
    Syllable,
    SyllableResult,
    Timing,
    ToneGrade,
    Transcript,
    WordResult,
)
from app.scoring import feedback
from app.scoring.ctc import align, score_sounds
from app.scoring.matcher import match, score_sounds_base
from app.scoring.rhythm import score_rhythm
from app.scoring.tone import score_tones
from app.scoring.transcribe import transcribe

log = logging.getLogger(__name__)

# --- scoring.md ---------------------------------------------------------------
INITIAL_WEIGHT, FINAL_WEIGHT = 0.43, 0.57
GOOD_FROM, OK_FROM = 85, 70
RETRY_BELOW_COMPLETENESS = 50
WEIGHTS = {
    ("line", "spoken"): {"pronunciation": 0.71, "completeness": 0.29},
    ("line", "singing"): {"pronunciation": 0.60, "completeness": 0.25, "rhythm": 0.15},
    ("word", None): {"pronunciation": 0.50, "completeness": 0.20, "tone": 0.30},
}
WORST_FIRST: list[Status] = ["missing", "wrong", "ok", "good"]


def grade(audio: Audio, line: Line, target: str, mode: str | None, word_index: int | None) -> AttemptResult:
    expected, word_specs = _expected(line, target, mode, word_index)
    context = _context(line, target, mode, word_index)
    layers = config.layers_for(target, context["mode"], syllable_count=len(expected))
    transcript = transcribe(audio)
    if transcript.no_speech:
        return no_speech_result(**context)
    observed = match(expected, transcript.syllables)
    sounds = score_sounds_base(expected, observed)
    n = len(expected)
    spans = _optional("align", n, align, audio, expected) if layers.ctc_spans else None
    if layers.ctc_scores and spans is not None:
        finer = _optional("score_sounds", n, score_sounds, audio, expected, spans)
        if finer is not None:
            sounds = finer
    rhythm = None
    if layers.rhythm and spans is not None:
        rhythm = _optional("score_rhythm", n, score_rhythm, expected, spans)
    tones = None
    if layers.tone and (spans is not None or n == 1):
        tones = _optional("score_tones", n, score_tones, audio, expected, spans)
    return assemble(expected, observed, sounds, spans, rhythm, tones, transcript,
                    word_specs=word_specs, engine="whisper+ctc" if spans is not None else "whisper",
                    trim_offset_ms=audio.trim_offset_ms, **context)


def _optional(name: str, n: int, fn: Callable, *args):
    """fn(*args), or None if it raises or does not return one entry per expected syllable."""
    try:
        out = fn(*args)
        entries = out.syllables if isinstance(out, RhythmResult) else out
        if out is not None and len(entries) != n:
            raise ValueError(f"returned {len(entries)} entries for {n} expected syllables")
        return out
    except Exception:
        log.exception("%s failed; continuing without it", name)
        return None


def no_speech_result(*, line_index: int, target: str, mode: str | None, word_index: int | None) -> AttemptResult:
    return AttemptResult(
        attempt_id="", song_id="", line_index=line_index, word_index=word_index, target=target, mode=mode,
        status="no_speech", engine="whisper",
        scores=Scores(overall=None, pronunciation=None, completeness=None, rhythm=None, tone=None, melody=None),
        words=[], syllables=[], heard=None,
        next_step=LineStep(type="retry_line", message="We didn't hear anything. Try again."),
    )


def assemble(
    expected: Sequence[Syllable],
    observed: Sequence[Syllable | None],
    sounds: Sequence[SoundScore | None],
    spans: Sequence[Span | None] | None,
    rhythm: RhythmResult | None,
    tones: Sequence[ToneGrade | None] | None,
    transcript: Transcript,
    *,
    word_specs: list[tuple[int, str, list[int]]],
    engine: str,
    trim_offset_ms: int,
    line_index: int,
    target: str,
    mode: str | None,
    word_index: int | None,
) -> AttemptResult:
    n = len(expected)
    for name, layer in (("observed", observed), ("sounds", sounds), ("spans", spans), ("tones", tones)):
        if layer is not None and len(layer) != n:
            raise ValueError(f"{name} has {len(layer)} entries for {n} expected syllables")
    if rhythm is not None and len(rhythm.syllables) != n:
        raise ValueError(f"rhythm has {len(rhythm.syllables)} entries for {n} expected syllables")

    syllables = [
        _syllable_result(i, expected[i], sounds[i],
                         spans[i] if spans else None,
                         rhythm.syllables[i] if rhythm else None,
                         tones[i] if tones else None, trim_offset_ms)
        for i in range(n)
    ]
    words = [_word_result(idx, text, indices, expected, syllables) for idx, text, indices in word_specs]

    sung = [s for s in syllables if s.status != "missing"]
    pronunciation = _mean([s.score or 0 for s in sung]) if sung else None
    completeness = round_half_up(100 * len(sung) / n) if n else None
    tone_scores = [t.score for t in (tones or []) if t is not None and t.score is not None]
    components = {
        "pronunciation": pronunciation,
        "completeness": completeness,
        "rhythm": rhythm.score if rhythm else None,
        "tone": _mean(tone_scores) if tone_scores else None,
    }
    weights = WEIGHTS[(target, mode if target == "line" else None)]
    scores = Scores(overall=_overall(components, weights), melody=None, **components)

    return AttemptResult(
        attempt_id="", song_id="", line_index=line_index, word_index=word_index, target=target, mode=mode,
        status="ok", engine=engine, scores=scores, words=words, syllables=syllables,
        heard=Heard(hanzi=transcript.text, pinyin=" ".join(s.pinyin for s in transcript.syllables)),
        next_step=_next_step(words, completeness, target),
    )


def round_half_up(x: float) -> int:
    return int(x + 0.5)


def _rhythm_code(rhythm_syllable: RhythmSyllable | None) -> str | None:
    """Early or late when this syllable's rhythm score is below the good line. None when it is on time.

    85 on the rhythm formula (100 × e^(−|offset| / 400 ms)) is about 65 ms off.
    An offset of 0 has no direction, so it never produces a message.
    """
    if rhythm_syllable is None or rhythm_syllable.score >= GOOD_FROM or rhythm_syllable.offset_ms == 0:
        return None
    return "RHYTHM_EARLY" if rhythm_syllable.offset_ms < 0 else "RHYTHM_LATE"


def status_for(score: int) -> Status:
    if score >= GOOD_FROM:
        return "good"
    return "ok" if score >= OK_FROM else "wrong"


def _mean(values: Sequence[int]) -> int:
    return round_half_up(sum(values) / len(values))


def _overall(components: dict[str, int | None], weights: dict[str, float]) -> int | None:
    present = {k: w for k, w in weights.items() if components[k] is not None}
    if not present:
        return None
    total = sum(present.values())
    return round_half_up(sum(w * (components[k] or 0) for k, w in present.items()) / total)


def _syllable_result(index, e, sound, span, rhythm_syllable, tone, trim_offset_ms) -> SyllableResult:
    if sound is None:
        status: Status = "missing"
        score = 0
        initial = Part(expected=e.initial, heard=None, score=0) if e.initial else None
        final = Part(expected=e.final, heard=None, score=0)
    else:
        initial, final = sound.initial, sound.final
        final_score = final.score or 0
        if initial is None:
            score = final_score
        else:
            score = round_half_up(INITIAL_WEIGHT * (initial.score or 0) + FINAL_WEIGHT * final_score)
        status = status_for(score)
    if status == "good" and tone is not None and tone.heard is not None and tone.heard != tone.expected:
        # A mismatched tone scores at most 60 (scoring.md), so this lands on "wrong".
        # The "ok" fallback only matters if a mismatch ever scores in the good band.
        lowered = status_for(tone.score) if tone.score is not None else "wrong"
        status = "ok" if lowered == "good" else lowered
    rhythm_code = _rhythm_code(rhythm_syllable)
    if status == "good" and rhythm_code is not None and rhythm_syllable is not None:
        status = status_for(rhythm_syllable.score)
    timing = None
    if span is not None:
        timing = Timing(start_ms=span.start_ms + trim_offset_ms, end_ms=span.end_ms + trim_offset_ms,
                        offset_ms=rhythm_syllable.offset_ms if rhythm_syllable else None,
                        score=rhythm_syllable.score if rhythm_syllable else None)
    return SyllableResult(
        index=index, hanzi=e.hanzi, pinyin=e.pinyin, status=status, score=score,
        initial=initial, final=final, tone=tone, timing=timing,
        feedback=None if status == "good" else feedback.pick(sound, tone, rhythm_code),
    )


def _word_result(index, text, indices, expected, syllables) -> WordResult:
    parts = [syllables[i] for i in indices]
    status = next(st for st in WORST_FIRST if any(p.status == st for p in parts))
    return WordResult(index=index, text=text, pinyin=" ".join(expected[i].pinyin for i in indices),
                      status=status, score=_mean([p.score or 0 for p in parts]), syllable_indices=indices)


def _next_step(words: list[WordResult], completeness: int | None, target: str) -> PracticeWordStep | LineStep:
    if target == "line" and completeness is not None and completeness < RETRY_BELOW_COMPLETENESS:
        return LineStep(type="retry_line", message="Part of the line was missing. Listen again and retry.")
    weak = [w for w in words if w.status != "good"]
    if weak:
        worst = min(weak, key=lambda w: w.score or 0)
        return PracticeWordStep(type="practice_word", word_index=worst.index,
                                message=f"Say {worst.text} ({worst.pinyin}) on its own, then retry the line.")
    if target == "word":
        return LineStep(type="retry_line", message="Well said. Now retry the line.")
    return LineStep(type="next_line", message="Nice! On to the next line.")


def _expected(line: Line, target: str, mode: str | None, word_index: int | None):
    if target == "line":
        if mode not in ("spoken", "singing"):
            raise ValueError("mode must be 'spoken' or 'singing' when target is 'line'")
        return line.syllables, [(w.index, w.text, w.syllable_indices) for w in line.words]
    if target == "word":
        if word_index is None:
            raise ValueError("word_index is required when target is 'word'")
        word = songs.get_word(line, word_index)
        syllables = songs.word_syllables(line, word_index)
        return syllables, [(word.index, word.text, list(range(len(syllables))))]
    raise ValueError("target must be 'line' or 'word'")


def _context(line: Line, target: str, mode: str | None, word_index: int | None) -> dict:
    return {"line_index": line.index, "target": target,
            "mode": mode if target == "line" else None,
            "word_index": word_index if target == "word" else None}
