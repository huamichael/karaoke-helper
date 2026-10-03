"""Mock grader, selected with GRADER=mock.

Returns a valid, deterministic AttemptResult built from the expected line without
looking at the audio. It cycles through every status so the frontend can be built
before the real grader exists.

Owner: B. Spec: docs/tasks/backend-api-whisper.md.
"""

from app import songs
from app.schemas import (
    AttemptResult,
    Feedback,
    Heard,
    Line,
    LineStep,
    LyricSyllable,
    Part,
    PracticeWordStep,
    Scores,
    Status,
    SyllableResult,
    WordResult,
)

NO_SPEECH_BYTES = 2048
CYCLE: list[Status] = ["good", "good", "ok", "good", "wrong", "good", "missing"]
# Canned numbers, not the scoring.md formulas: the mock only has to look plausible.
SCORE: dict[Status, int] = {"good": 100, "ok": 80, "wrong": 40, "missing": 0}
WORST_FIRST: list[Status] = ["missing", "wrong", "ok", "good"]


def grade_mock(
    data: bytes,
    song_id: str,
    line: Line,
    target: str,
    mode: str | None,
    word_index: int | None,
    attempt_id: str,
) -> AttemptResult:
    if target == "line":
        if mode not in ("spoken", "singing"):
            raise ValueError("mode must be 'spoken' or 'singing' when target is 'line'")
        expected = line.syllables
        word_specs = [(w.index, w.text, w.syllable_indices) for w in line.words]
    elif target == "word":
        if word_index is None:
            raise ValueError("word_index is required when target is 'word'")
        word = songs.get_word(line, word_index)
        expected = songs.word_syllables(line, word_index)
        word_specs = [(word.index, word.text, list(range(len(expected))))]
        mode = None
    else:
        raise ValueError("target must be 'line' or 'word'")

    base = {
        "attempt_id": attempt_id, "song_id": song_id, "line_index": line.index,
        "word_index": word_index if target == "word" else None,
        "target": target, "mode": mode, "engine": "mock",
    }
    if len(data) < NO_SPEECH_BYTES:
        return AttemptResult(
            **base, status="no_speech",
            scores=Scores(overall=None, pronunciation=None, completeness=None, rhythm=None, tone=None, melody=None),
            words=[], syllables=[], heard=None,
            next_step=LineStep(type="retry_line", message="We didn't hear anything. Try again."),
        )

    syllables = [_syllable(pos, s, CYCLE[(s.index + line.index) % len(CYCLE)]) for pos, s in enumerate(expected)]
    words = [_word(i, text, idx, syllables) for i, text, idx in word_specs]

    sung = [r for r in syllables if r.status != "missing"]
    pronunciation = round(sum(r.score or 0 for r in sung) / len(sung)) if sung else None
    completeness = round(100 * len(sung) / len(syllables))
    overall = completeness if pronunciation is None else round((pronunciation + completeness) / 2)
    heard = Heard(hanzi="".join(r.hanzi for r in sung), pinyin=" ".join(r.pinyin for r in sung)) if sung else None

    return AttemptResult(
        **base, status="ok",
        scores=Scores(overall=overall, pronunciation=pronunciation, completeness=completeness,
                      rhythm=None, tone=None, melody=None),
        words=words, syllables=syllables, heard=heard,
        next_step=_next_step(words, target),
    )


def _syllable(pos: int, s: LyricSyllable, status: Status) -> SyllableResult:
    score = SCORE[status]
    off = "initial" if s.initial and status in ("ok", "wrong") else "final"

    def part(name: str, expected: str) -> Part:
        if status == "missing":
            return Part(expected=expected, heard=None, score=0)
        if status == "good" or name != off:
            return Part(expected=expected, heard=expected, score=100)
        return Part(expected=expected, heard="?", score=score)

    if status == "good":
        feedback = None
    elif status == "missing":
        feedback = Feedback(code="MISSING", message="We didn't hear this syllable.")
    else:
        feedback = Feedback(code=f"{off.upper()}_OTHER", message=f"Mock feedback: the {off} of {s.pinyin} was off.")

    return SyllableResult(
        index=pos, hanzi=s.hanzi, pinyin=s.pinyin, status=status, score=score,
        initial=part("initial", s.initial) if s.initial else None,
        final=part("final", s.final),
        tone=None, timing=None, feedback=feedback,
    )


def _word(index: int, text: str, syllable_indices: list[int], syllables: list[SyllableResult]) -> WordResult:
    parts = [syllables[i] for i in syllable_indices]
    status = next(st for st in WORST_FIRST if any(p.status == st for p in parts))
    return WordResult(
        index=index, text=text, pinyin=" ".join(p.pinyin for p in parts), status=status,
        score=round(sum(p.score or 0 for p in parts) / len(parts)), syllable_indices=syllable_indices,
    )


def _next_step(words: list[WordResult], target: str) -> PracticeWordStep | LineStep:
    weak = [w for w in words if w.status != "good"]
    if not weak:
        if target == "word":
            return LineStep(type="retry_line", message="Well said. Now retry the line.")
        return LineStep(type="next_line", message="Nice! On to the next line.")
    worst = min(weak, key=lambda w: w.score or 0)
    return PracticeWordStep(type="practice_word", word_index=worst.index,
                            message=f"Say {worst.text} ({worst.pinyin}) on its own, then retry the line.")
