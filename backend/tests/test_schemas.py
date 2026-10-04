"""Tests for the shared types in app/schemas.py.

The field lists and example payloads are copied from docs/contracts/, so a
schema that drifts from the contract fails here.

Owner: B.
"""

import dataclasses

import numpy as np
import pytest
from pydantic import ValidationError

from app import schemas as s

CONTRACT_FIELDS = {
    # data-model.md
    s.Syllable: ["hanzi", "pinyin", "pinyin_numeric", "initial", "final", "tone", "start_ms", "end_ms"],
    s.LyricSyllable: ["hanzi", "pinyin", "pinyin_numeric", "initial", "final", "tone", "start_ms", "end_ms",
                      "index", "word_index"],
    s.Word: ["index", "text", "syllable_indices", "gloss", "audio_url"],
    s.Line: ["index", "start_ms", "end_ms", "text", "translation", "syllables", "words"],
    s.Song: ["id", "title", "artist", "line_count", "audio_url", "lines"],
    # backend-interfaces.md section 2
    s.Transcript: ["text", "syllables", "no_speech"],
    s.Span: ["start_ms", "end_ms", "confidence"],
    s.Part: ["expected", "heard", "score"],
    s.SoundScore: ["initial", "final"],
    s.ToneGrade: ["expected", "heard", "score"],
    s.RhythmSyllable: ["offset_ms", "score"],
    s.RhythmResult: ["score", "syllables"],
    # api.md
    s.SongSummary: ["id", "title", "artist", "line_count"],
    s.Scores: ["overall", "pronunciation", "completeness", "rhythm", "tone", "melody"],
    s.WordResult: ["index", "text", "pinyin", "status", "score", "syllable_indices"],
    s.SyllableResult: ["index", "hanzi", "pinyin", "status", "score", "initial", "final", "tone", "timing",
                       "feedback"],
    s.Timing: ["start_ms", "end_ms", "offset_ms", "score"],
    s.Heard: ["hanzi", "pinyin"],
    s.AttemptResult: ["attempt_id", "song_id", "line_index", "word_index", "target", "mode", "status", "engine",
                      "scores", "words", "syllables", "heard", "next_step"],
    s.ErrorBody: ["error"],
    s.ErrorDetail: ["code", "message"],
    s.Health: ["status", "grader"],
}

# data-model.md section 6
REFERENCE_NI = {
    "index": 3, "word_index": 3,
    "hanzi": "你", "pinyin": "nǐ", "pinyin_numeric": "ni3",
    "initial": "n", "final": "i", "tone": 3,
    "start_ms": 17840, "end_ms": 18210,
}
OBSERVED_LI = {
    "hanzi": "李", "pinyin": "lǐ", "pinyin_numeric": "li3",
    "initial": "l", "final": "i", "tone": None,
    "start_ms": None, "end_ms": None,
}

# api.md "Example result", with only the flagged word and syllable
EXAMPLE_RESULT = {
    "attempt_id": "att_0007",
    "song_id": "song_001",
    "line_index": 3,
    "word_index": None,
    "target": "line",
    "mode": "spoken",
    "status": "ok",
    "engine": "whisper",
    "scores": {
        "overall": 98, "pronunciation": 97, "completeness": 100,
        "rhythm": None, "tone": None, "melody": None,
    },
    "words": [
        {"index": 3, "text": "你", "pinyin": "nǐ", "status": "ok", "score": 83, "syllable_indices": [3]},
    ],
    "syllables": [
        {
            "index": 3, "hanzi": "你", "pinyin": "nǐ",
            "status": "ok", "score": 83,
            "initial": {"expected": "n", "heard": "l", "score": 60},
            "final": {"expected": "i", "heard": "i", "score": 100},
            "tone": None,
            "timing": None,
            "feedback": {
                "code": "INITIAL_N_L",
                "message": "How to say \"nǐ\": Start with \"n\": tongue tip behind your top teeth, "
                           "with the air going through your nose.",
            },
        },
    ],
    "heard": {"hanzi": "我想和李一起", "pinyin": "wǒ xiǎng hé lǐ yì qǐ"},
    "next_step": {
        "type": "practice_word", "word_index": 3,
        "message": "Say 你 (nǐ) on its own, then retry the line.",
    },
}


def with_changes(base: dict, **changes) -> dict:
    return {**base, **changes}


@pytest.mark.parametrize("model, fields", CONTRACT_FIELDS.items(), ids=lambda x: getattr(x, "__name__", ""))
def test_field_names_match_contract(model, fields):
    assert list(model.model_fields) == fields


def test_audio_is_a_dataclass_with_contract_fields():
    assert [f.name for f in dataclasses.fields(s.Audio)] == ["samples", "sample_rate", "trim_offset_ms"]
    audio = s.Audio(samples=np.zeros(16000, dtype=np.float32), sample_rate=16000, trim_offset_ms=150)
    assert audio.samples.shape == (16000,)


def test_data_model_worked_example_round_trips():
    ref = s.LyricSyllable.model_validate(REFERENCE_NI)
    obs = s.Syllable.model_validate(OBSERVED_LI)
    assert ref.model_dump() == REFERENCE_NI
    assert obs.model_dump() == OBSERVED_LI
    assert (ref.initial, obs.initial) == ("n", "l")


def test_api_example_result_round_trips():
    result = s.AttemptResult.model_validate(EXAMPLE_RESULT)
    assert result.model_dump(mode="json") == EXAMPLE_RESULT
    assert isinstance(result.next_step, s.PracticeWordStep)
    assert result.next_step.word_index == 3


@pytest.mark.parametrize("step_type", ["retry_line", "next_line"])
def test_line_next_steps_parse(step_type):
    data = with_changes(EXAMPLE_RESULT, next_step={"type": step_type, "message": "Try again."})
    result = s.AttemptResult.model_validate(data)
    assert isinstance(result.next_step, s.LineStep)
    assert result.next_step.type == step_type


def test_no_speech_result_with_null_scores_and_empty_lists():
    data = with_changes(
        EXAMPLE_RESULT,
        status="no_speech",
        scores={k: None for k in EXAMPLE_RESULT["scores"]},
        words=[], syllables=[], heard=None,
        next_step={"type": "retry_line", "message": "We didn't hear anything."},
    )
    assert s.AttemptResult.model_validate(data).status == "no_speech"


def test_word_target_has_null_mode():
    data = with_changes(EXAMPLE_RESULT, target="word", mode=None, word_index=3)
    result = s.AttemptResult.model_validate(data)
    assert (result.target, result.mode, result.word_index) == ("word", None, 3)


@pytest.mark.parametrize("tone", [1, 5, None])
def test_tone_boundaries_accepted(tone):
    assert s.Syllable.model_validate(with_changes(OBSERVED_LI, tone=tone)).tone == tone


def test_lyric_syllable_requires_tone():
    with pytest.raises(ValidationError):
        s.LyricSyllable.model_validate(with_changes(REFERENCE_NI, tone=None))
    with pytest.raises(ValidationError):
        s.LyricSyllable.model_validate(with_changes(REFERENCE_NI, tone=6))


def test_empty_initial_accepted():
    wo = {"hanzi": "我", "pinyin": "wǒ", "pinyin_numeric": "wo3", "initial": "", "final": "uo",
          "tone": 3, "start_ms": None, "end_ms": None}
    assert s.Syllable.model_validate(wo).initial == ""


@pytest.mark.parametrize("tone", [0, 6, -1])
def test_tone_out_of_range_rejected(tone):
    with pytest.raises(ValidationError):
        s.Syllable.model_validate(with_changes(OBSERVED_LI, tone=tone))


@pytest.mark.parametrize("score", [0, 100, None])
def test_score_boundaries_accepted(score):
    assert s.Part(expected="n", heard="l", score=score).score == score


@pytest.mark.parametrize("score", [-1, 101])
def test_score_out_of_range_rejected(score):
    with pytest.raises(ValidationError):
        s.Part(expected="n", heard="l", score=score)
    with pytest.raises(ValidationError):
        s.Scores(overall=score, pronunciation=None, completeness=None, rhythm=None, tone=None, melody=None)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_span_confidence_out_of_range_rejected(confidence):
    with pytest.raises(ValidationError):
        s.Span(start_ms=0, end_ms=100, confidence=confidence)


@pytest.mark.parametrize("field, bad", [
    ("target", "song"),
    ("mode", "rap"),
    ("status", "great"),
])
def test_bad_enum_values_rejected(field, bad):
    with pytest.raises(ValidationError):
        s.AttemptResult.model_validate(with_changes(EXAMPLE_RESULT, **{field: bad}))


def test_bad_word_status_rejected():
    word = with_changes(EXAMPLE_RESULT["words"][0], status="great")
    with pytest.raises(ValidationError):
        s.AttemptResult.model_validate(with_changes(EXAMPLE_RESULT, words=[word]))


def test_practice_word_step_requires_word_index():
    with pytest.raises(ValidationError):
        s.AttemptResult.model_validate(
            with_changes(EXAMPLE_RESULT, next_step={"type": "practice_word", "message": "Say it."})
        )


def test_unknown_next_step_type_rejected():
    with pytest.raises(ValidationError):
        s.AttemptResult.model_validate(
            with_changes(EXAMPLE_RESULT, next_step={"type": "give_up", "message": "Bye."})
        )


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        s.LyricSyllable.model_validate(with_changes(REFERENCE_NI, pinyin_num="ni3"))


def test_missing_required_field_rejected():
    data = {k: v for k, v in REFERENCE_NI.items() if k != "word_index"}
    with pytest.raises(ValidationError):
        s.LyricSyllable.model_validate(data)


def test_json_schemas_generate():
    for model in (s.Song, s.SongSummary, s.AttemptResult, s.ErrorBody, s.Health):
        assert model.model_json_schema()["type"] == "object"
