"""Deterministic CTC, pipeline, and evaluation tests; no model downloads."""
from __future__ import annotations

import gc
import itertools
import json
from pathlib import Path
import wave

import numpy as np
import pytest
import torch
import torchaudio

from app.schemas import Audio, Line, SoundScore, Span, Syllable
from app.scoring import ctc
from pipeline import align_track
from tests import eval_ctc


def syllable(numeric="a1", initial="", final="a"):
    return Syllable(hanzi="啊", pinyin=numeric, pinyin_numeric=numeric, initial=initial,
                    final=final, tone=int(numeric[-1]), start_ms=None, end_ms=None)


def audio(ms=1000):
    return Audio(samples=np.full(ms * 16, 0.1, dtype=np.float32), sample_rate=16000, trim_offset_ms=150)


def emission(path, strength=0.94):
    dictionary = {letter: index for index, letter in enumerate("-abcdefghijklmnopqrstuvwxyz")}
    probabilities = np.full((len(path), len(dictionary)), (1 - strength) / (len(dictionary) - 1), dtype=np.float32)
    probabilities[np.arange(len(path)), [dictionary[ch] for ch in path]] = strength
    return ctc._Emission(np.log(probabilities), dictionary, 20)


@pytest.fixture(autouse=True)
def clean_cache():
    ctc._cache.clear()
    yield
    ctc._cache.clear()


def install(monkeypatch, data):
    calls = []
    monkeypatch.setattr(ctc, "_infer", lambda a: calls.append(a) or data)
    monkeypatch.setattr(ctc, "_runtime", lambda: (torch, torchaudio, None, data.dictionary, data.frame_ms))
    return calls


@pytest.mark.parametrize("numeric,initial,final,letters", [
    ("jiu4", "j", "iou", "jiu"), ("hui4", "h", "uei", "hui"),
    ("wo3", "", "uo", "wo"), ("nv3", "n", "v", "nv"), ("de5", "d", "e", "de"),
])
def test_numeric_standard_spelling(numeric, initial, final, letters):
    assert ctc._letters(syllable(numeric, initial, final)) == letters


@pytest.mark.parametrize("numeric,initial,final,kind,partner,letters", [
    ("zhun3", "zh", "uen", "initial", "z", "zun"),
    ("san1", "s", "an", "final", "ang", "sang"),
    ("zhun3", "zh", "uen", "final", "ueng", "zhueng"),
    ("wen2", "", "uen", "final", "ueng", "weng"),
    ("yin1", "", "in", "final", "ing", "ying"),
])
def test_variant_spelling(numeric, initial, final, kind, partner, letters):
    assert ctc._variant(syllable(numeric, initial, final), **{kind: partner}) == letters


def test_alignment_repeated_letters_and_exclusive_ends(monkeypatch):
    data = emission("aa-aa")
    install(monkeypatch, data)
    expected = [syllable(), syllable()]
    before = [s.model_dump() for s in expected]
    result = ctc.align(audio(), expected)
    assert [(s.start_ms, s.end_ms) for s in result] == [(0, 40), (60, 100)]
    assert all(s.confidence == pytest.approx(0.94) for s in result)
    assert [s.model_dump() for s in expected] == before


def test_alignment_groups_letters_and_leaves_trim_offset_to_grader(monkeypatch):
    install(monkeypatch, emission("--jjiiuu--wwoo--"))
    result = ctc.align(audio(), [syllable("jiu4", "j", "iou"), syllable("wo3", "", "uo")])
    assert [(s.start_ms, s.end_ms) for s in result] == [(40, 160), (200, 280)]


@pytest.mark.parametrize("path,strength", [("a", 0.94), ("aa", 0.09)])
def test_short_or_low_confidence_span_is_missing(monkeypatch, path, strength):
    install(monkeypatch, emission(path, strength))
    assert ctc.align(audio(), [syllable()]) == [None]


def test_exact_minimum_length_is_usable(monkeypatch):
    install(monkeypatch, emission("aa", 0.11))
    assert ctc.align(audio(), [syllable()])[0].end_ms == 40


def test_empty_silence_and_impossible_target_need_no_fake_spans(monkeypatch):
    assert ctc.align(audio(), []) == []
    assert ctc.align(Audio(np.zeros(16000, dtype=np.float32), 16000, 0), [syllable()]) == [None]
    install(monkeypatch, emission("aa"))
    assert ctc.align(audio(), [syllable(), syllable()]) == [None, None]


def test_invalid_audio_and_token_fail_loudly(monkeypatch):
    with pytest.raises(ValueError, match="16000"):
        ctc.align(Audio(np.ones(1000, dtype=np.float32), 8000, 0), [syllable()])
    with pytest.raises(ValueError, match="finite"):
        ctc.align(Audio(np.full(16000, np.nan, dtype=np.float32), 16000, 0), [syllable()])
    with pytest.raises(ValueError, match="pinyin_numeric"):
        ctc._letters(syllable().model_copy(update={"pinyin_numeric": "a"}))
    data = emission("aa")
    with pytest.raises(ValueError, match="vocabulary"):
        ctc._tokens("ü", data)


def test_inference_shared_by_alignment_and_scoring(monkeypatch):
    calls = install(monkeypatch, emission("nniiii"))
    recording = audio()
    expected = [syllable("ni3", "n", "i")]
    spans = ctc.align(recording, expected)
    assert isinstance(ctc.score_sounds(recording, expected, spans)[0], SoundScore)
    assert len(calls) == 1


def test_cache_is_bounded_and_releases_audio(monkeypatch):
    monkeypatch.setattr(ctc, "_infer", lambda _: emission("aa"))
    recordings = [audio() for _ in range(ctc.CACHE_SIZE + 3)]
    for recording in recordings:
        ctc._emissions(recording)
    assert len(ctc._cache) == ctc.CACHE_SIZE
    key = id(recordings[1])
    assert key not in ctc._cache
    key = id(recordings[-2])
    del recordings[-2]
    gc.collect()
    assert key not in ctc._cache


def test_confused_initial_wins_without_changing_final(monkeypatch):
    install(monkeypatch, emission("--lliiii--"))
    result = ctc.score_sounds(audio(), [syllable("ni3", "n", "i")], [Span(start_ms=40, end_ms=160, confidence=0.94)])[0]
    assert result.initial.heard == "l" and result.initial.score <= 60
    assert result.final.heard == "i" and result.final.score == 94


def test_confused_final_wins_without_changing_initial(monkeypatch):
    install(monkeypatch, emission("--ssaannnggg--"))
    result = ctc.score_sounds(audio(), [syllable("san1", "s", "an")], [Span(start_ms=40, end_ms=240, confidence=0.94)])[0]
    assert result.final.heard == "ang" and result.final.score <= 60
    assert result.initial.heard == "s"


def test_scoring_preserves_missing_indices_and_no_initial(monkeypatch):
    install(monkeypatch, emission("aann"))
    result = ctc.score_sounds(audio(), [syllable("an1", "", "an"), syllable()],
                              [Span(start_ms=0, end_ms=80, confidence=0.95), None])
    assert len(result) == 2 and result[1] is None and result[0].initial is None
    with pytest.raises(ValueError, match="one entry"):
        ctc.score_sounds(audio(), [syllable()], [])


def collapse(path, blank):
    return [value for i, value in enumerate(path) if value != blank and (i == 0 or path[i - 1] != value)]


@pytest.mark.parametrize("targets", [[1], [1, 2], [1, 1], [2, 1, 2]])
def test_viterbi_matches_exhaustive_ctc_paths(targets):
    probabilities = np.array([[.4, .4, .2], [.2, .5, .3], [.6, .1, .3], [.3, .4, .3]])
    logs = np.log(probabilities)
    complete = [sum(logs[t, value] for t, value in enumerate(path)) / 4
                for path in itertools.product(range(3), repeat=4) if collapse(path, 0) == targets]
    assert ctc._best_path_mean(logs, targets, 0) == pytest.approx(max(complete))


def test_viterbi_repeated_letter_needs_blank_and_no_partial_pass():
    logs = np.log(np.array([[.1, .9], [.1, .9]]))
    assert ctc._best_path_mean(logs, [1, 1], 0) == -np.inf


@pytest.mark.parametrize("margin", [-100, -1, -.001, 0, .001, 1, 100])
def test_component_score_range_and_wrong_cap(margin):
    score = ctc._margin_score(-2 + margin, -2)
    assert 0 <= score <= 100
    if margin < 0:
        assert score <= 60
    if margin == 0:
        assert score == 70


def fixture_line(name="yueliang"):
    path = Path(__file__).parent / "fixtures" / "lines" / f"{name}.json"
    return Line.model_validate_json(path.read_text())


def song_bundle():
    from app.schemas import Song
    line = fixture_line().model_copy(deep=True)
    line.start_ms, line.end_ms = 100, 800
    return Song(id="test-song", title="Test", artist="Test", line_count=1,
                audio_url="/media/songs/test-song/audio.mp3", lines=[line])


def test_pipeline_crop_origin_and_only_timing_fields_change(monkeypatch):
    song = song_bundle()
    before = song.model_dump()
    seen = []
    def fake(recording, expected):
        seen.append(recording)
        return [Span(start_ms=10 + 80 * i, end_ms=70 + 80 * i, confidence=.9) if i != 2 else None
                for i in range(len(expected))]
    monkeypatch.setattr(align_track, "align", fake)
    result, reports = align_track.align_song(song, audio(1200).samples)
    assert len(seen[0].samples) == 16000 and seen[0].trim_offset_ms == 0
    assert result.lines[0].syllables[0].start_ms == 10  # clamped crop starts at 0
    assert result.lines[0].syllables[2].start_ms is None
    assert "missing=1/7" in reports[0]
    assert song.model_dump() == before
    for original, aligned in zip(song.lines[0].syllables, result.lines[0].syllables):
        assert original.model_dump(exclude={"start_ms", "end_ms"}) == aligned.model_dump(exclude={"start_ms", "end_ms"})


def test_pipeline_track_offset_includes_context(monkeypatch):
    song = song_bundle()
    song.lines[0].start_ms, song.lines[0].end_ms = 500, 1000
    monkeypatch.setattr(align_track, "align", lambda a, exp: [Span(start_ms=200, end_ms=240, confidence=.9)] * len(exp))
    result, _ = align_track.align_song(song, audio(1500).samples)
    assert result.lines[0].syllables[0].start_ms == 500


def test_pipeline_failure_and_concurrent_edit_preserve_file(tmp_path, monkeypatch):
    song = song_bundle()
    path = tmp_path / "song.json"
    original = song.model_dump_json()
    path.write_text(original)
    monkeypatch.setattr(align_track, "align", lambda *_: (_ for _ in ()).throw(RuntimeError("model failed")))
    with pytest.raises(RuntimeError, match="model failed"):
        updated, _ = align_track.align_song(song, audio().samples)
        align_track.write_atomic(path, updated, original)
    assert path.read_text() == original
    path.write_text(original + "\n")
    with pytest.raises(RuntimeError, match="changed"):
        align_track.write_atomic(path, song, original)
    assert path.read_text() == original + "\n"
    assert not list(tmp_path.glob("*.tmp"))


def test_pipeline_atomic_write_validates_and_preserves_bundle(tmp_path):
    path = tmp_path / "song.json"
    song = song_bundle()
    original = song.model_dump_json()
    path.write_text(original)
    align_track.write_atomic(path, song, original)
    assert json.loads(path.read_text()) == song.model_dump()


def test_pipeline_decode_wav_without_silence_trim(tmp_path):
    path = tmp_path / "silence.wav"
    with wave.open(str(path), "wb") as handle:
        handle.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        handle.writeframes(np.zeros(16000, dtype="<i2").tobytes())
    result = align_track.decode_track(path)
    assert len(result) == 16000 and result.dtype == np.float32
    assert not result.any()


def test_eval_requires_annotations_for_ambiguous_errors():
    line = fixture_line("yijianmei")
    line.syllables[4] = line.syllables[5].model_copy(deep=True)
    with pytest.raises(ValueError, match="provide --labels"):
        eval_ctc.error_indices(line, "error-n-l")
    assert eval_ctc.error_indices(line, "error-n-l", [4]) == {4}
    assert eval_ctc.error_indices(line, "missing-3") == {3}
    with pytest.raises(ValueError, match="zero-based"):
        eval_ctc.error_indices(line, "missing-999")
    assert eval_ctc.error_indices(line, "spoken") == set()


@pytest.mark.parametrize("name,variant,index", [
    ("yueliang", "error-1-iang-ian", 1),
    ("yijianmei", "error-2-ing-in", 2),
    ("jasmine", "error-4-l-n", 4),
])
def test_eval_session_errors_use_the_explicit_index(name, variant, index):
    line = fixture_line(name)
    assert eval_ctc.error_indices(line, variant) == {index}
    assert eval_ctc.error_indices(line, variant, [index]) == {index}
    with pytest.raises(ValueError, match="contradict"):
        eval_ctc.error_indices(line, variant, [])


@pytest.mark.parametrize("variant", ["error-2-iang-ian", "error-99-iang-ian", "error-1-iang-ang"])
def test_eval_indexed_errors_must_match_the_line(variant):
    with pytest.raises(ValueError, match="expected confused sound"):
        eval_ctc.error_indices(fixture_line(), variant)


@pytest.mark.parametrize("annotation", [[True], [1.0], ["1"], [[1]], [-1], [99]])
def test_eval_bad_labels_fail_before_building_sets(annotation):
    with pytest.raises(ValueError, match="zero-based"):
        eval_ctc.error_indices(fixture_line(), "error-1-iang-ian", annotation)


def test_eval_missing_labels_cannot_override_filename():
    with pytest.raises(ValueError, match="contradict"):
        eval_ctc.error_indices(fixture_line(), "missing-3", [4])


@pytest.mark.parametrize("stem,expected", [
    ("yueliang__error-1-iang-ian__mei", ("yueliang", "error-1-iang-ian", "mei")),
    ("yueliang__spoken__rayan", ("yueliang", "spoken", "rayan")),
    ("yueliang__error-iang-ian", ("yueliang", "error-iang-ian", "legacy")),
])
def test_eval_recording_names(stem, expected):
    assert eval_ctc.recording_name(Path(stem + ".wav")) == expected


@pytest.mark.parametrize("stem", ["yueliang", "yueliang__correct__Mei", "yueliang__correct__mei1",
                                        "yueliang__correct__mei__extra", "..__correct__mei"])
def test_eval_invalid_recording_names(stem):
    with pytest.raises(ValueError, match="name"):
        eval_ctc.recording_name(Path(stem + ".wav"))


def test_eval_missing_recordings_are_not_a_pass(tmp_path):
    with pytest.raises(ValueError, match="checkpoint B is pending"):
        eval_ctc.evaluate(tmp_path, {}, tmp_path / "clips")


def test_eval_reports_caught_errors_and_false_flags(tmp_path, monkeypatch, capsys):
    from app.schemas import Transcript
    from app.scoring.matcher import score_sounds_base
    line = fixture_line()
    (tmp_path / "lines").mkdir()
    (tmp_path / "audio").mkdir()
    (tmp_path / "lines" / "test.json").write_text(line.model_dump_json())
    for variant, speaker in (("correct", "mei"), ("missing-3", "rayan")):
        with wave.open(str(tmp_path / "audio" / f"test__{variant}__{speaker}.wav"), "wb") as handle:
            handle.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            handle.writeframes(np.zeros(16000, dtype="<i2").tobytes())
    monkeypatch.setattr(eval_ctc, "transcribe", lambda _: Transcript(text=line.text, syllables=line.syllables, no_speech=False))
    monkeypatch.setattr(ctc, "align", lambda a, exp: [None] * len(exp))
    finer = score_sounds_base(line.syllables, line.syllables)
    finer[3] = None
    monkeypatch.setattr(ctc, "score_sounds", lambda *_: finer)
    report = tmp_path / "reports" / "checkpoint.json"
    assert eval_ctc.evaluate(tmp_path, {}, tmp_path / "clips", report) == 0
    output = capsys.readouterr().out
    assert "whisper: errors caught 0/1; correct syllables wrongly flagged 0/13" in output
    assert "ctc: errors caught 1/1; correct syllables wrongly flagged 1/13" in output
    data = json.loads(report.read_text())
    assert data["totals"]["ctc"] == {"caught": 1, "errors": 1, "false_flags": 1, "correct": 13}
    assert data["speakers"]["mei"]["ctc"]["false_flags"] == 1
    assert data["speakers"]["rayan"]["ctc"]["caught"] == 1
    assert data["recordings"][1]["error_indices"] == [3]
    assert len(data["recordings"][0]["syllables"]) == len(line.syllables)
    assert data["recordings"][1]["syllables"][3]["ctc"]["flagged"] is True
    assert data["checkpoint_decision"] == "pending team review"


def make_eval_fixtures(folder, names):
    (folder / "lines").mkdir()
    (folder / "audio").mkdir()
    (folder / "lines" / "yueliang.json").write_text(fixture_line().model_dump_json())
    for name in names:
        with wave.open(str(folder / "audio" / name), "wb") as handle:
            handle.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            handle.writeframes(np.zeros(16000, dtype="<i2").tobytes())


@pytest.mark.parametrize("problem", ["label", "filename", "format", "truncated"])
def test_eval_preflights_all_recordings_before_models(tmp_path, monkeypatch, problem):
    names = ["yueliang__correct__mei.wav", "yueliang__spoken__mei.wav"]
    make_eval_fixtures(tmp_path, names)
    labels = {}
    path = tmp_path / "audio" / names[1]
    if problem == "label":
        labels = {"typo.wav": [1]}
    elif problem == "filename":
        path.rename(path.with_name("yueliang__error-2-iang-ian__mei.wav"))
    elif problem == "format":
        with wave.open(str(path), "wb") as handle:
            handle.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            handle.writeframes(np.zeros(8000, dtype="<i2").tobytes())
    else:
        path.write_bytes(path.read_bytes()[:-2])
    monkeypatch.setattr(eval_ctc, "transcribe", lambda _: pytest.fail("model ran before preflight"))
    monkeypatch.setattr(ctc, "align", lambda *_: pytest.fail("CTC ran before preflight"))
    with pytest.raises(ValueError):
        eval_ctc.evaluate(tmp_path, labels, tmp_path / "clips")


def test_eval_no_speech_uses_the_production_gate(tmp_path, monkeypatch):
    from app.schemas import Transcript
    make_eval_fixtures(tmp_path, ["yueliang__correct__mei.wav"])
    monkeypatch.setattr(eval_ctc, "transcribe", lambda _: Transcript(text="", syllables=[], no_speech=True))
    monkeypatch.setattr(ctc, "align", lambda *_: pytest.fail("CTC must not run on no_speech"))
    report = tmp_path / "report.json"
    eval_ctc.evaluate(tmp_path, {}, tmp_path / "clips", report)
    data = json.loads(report.read_text())
    assert data["totals"]["whisper"]["false_flags"] == 7
    assert data["totals"]["ctc"]["false_flags"] == 7
    assert data["recordings"][0]["no_speech"] is True
    assert not list((tmp_path / "clips").glob("*.wav"))


def test_export_clips_uses_trimmed_sample_times(tmp_path):
    recording = audio()
    recording.samples[:1600] = .25
    eval_ctc.export_spans(recording, [Span(start_ms=0, end_ms=100, confidence=1)], tmp_path, "clip")
    with wave.open(str(tmp_path / "clip__00.wav"), "rb") as handle:
        assert handle.getnframes() == 1600
        assert np.frombuffer(handle.readframes(1600), dtype="<i2")[0] == 8191
