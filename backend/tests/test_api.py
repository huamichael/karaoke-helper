"""Tests for the HTTP routes, run against the mock grader.

Checks response shapes and the error codes in docs/contracts/api.md.

Owner: B.
"""

import io
import json
import re
import wave
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import attempts, main, songs
from app.audio import BadAudio
from app.schemas import AttemptResult, ErrorBody, LineStep, Scores
from app.scoring import transcribe as tr

AUDIO = ("take.webm", b"\0" * 4096, "audio/webm")
LINE_FORM = {"song_id": "demo", "line_index": "0", "target": "line", "mode": "spoken"}
WORD_FORM = {"song_id": "demo", "line_index": "0", "target": "word", "word_index": "3"}


@pytest.fixture
def saved(monkeypatch, tmp_path):
    folder = tmp_path / "attempts"
    monkeypatch.setattr(attempts, "ATTEMPTS_DIR", folder)
    return folder


@pytest.fixture
def client(monkeypatch, saved):
    monkeypatch.setenv("GRADER", "mock")
    monkeypatch.setenv("WHISPER_ENGINE", "faster")
    return TestClient(main.app, raise_server_exceptions=False)


def post(client, form, audio=AUDIO):
    files = {"audio": audio} if audio else None
    return client.post("/api/v1/attempts", data=form, files=files)


def assert_error(response, status: int, code: str):
    assert response.status_code == status, response.text
    body = ErrorBody.model_validate(response.json())
    assert body.error.code == code
    assert body.error.message


# --- happy path ---------------------------------------------------------------


@pytest.mark.parametrize("grader", ["mock", "real"])
def test_health_reports_grader(client, monkeypatch, grader):
    monkeypatch.setenv("GRADER", grader)
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "grader": grader}


def test_song_list_includes_demo(client):
    r = client.get("/api/v1/songs")
    assert r.status_code == 200
    assert {"id": "demo", "title": "两只老虎", "artist": "Traditional", "line_count": 2} in r.json()


def test_song_returns_the_fixture_unchanged(client):
    r = client.get("/api/v1/songs/demo")
    assert r.status_code == 200
    on_disk = json.loads((songs.SONGS_DIR / "demo" / "song.json").read_text(encoding="utf-8"))
    assert r.json() == on_disk


def test_line_attempt_returns_mock_result(client):
    r = post(client, LINE_FORM)
    assert r.status_code == 200, r.text
    result = AttemptResult.model_validate(r.json())
    assert (result.song_id, result.line_index, result.target, result.mode) == ("demo", 0, "line", "spoken")
    assert (result.engine, result.status, result.word_index) == ("mock", "ok", None)
    assert len(result.syllables) == 8 and len(result.words) == 4
    assert result.attempt_id.startswith("att_")


def test_word_attempt_returns_mock_result(client):
    r = post(client, WORD_FORM)
    assert r.status_code == 200, r.text
    result = AttemptResult.model_validate(r.json())
    assert (result.target, result.mode, result.word_index) == ("word", None, 3)
    assert [w.text for w in result.words] == ["老虎"]


def test_attempt_ids_are_unique(client):
    ids = {post(client, LINE_FORM).json()["attempt_id"] for _ in range(3)}
    assert len(ids) == 3


def test_openapi_lists_routes_and_types(client):
    spec = client.get("/openapi.json").json()
    assert {"/api/v1/health", "/api/v1/songs", "/api/v1/songs/{song_id}", "/api/v1/attempts"} <= set(spec["paths"])
    assert {"AttemptResult", "Song", "SongSummary", "ErrorBody", "Health"} <= set(spec["components"]["schemas"])


def test_cors_allows_the_frontend_only(client):
    headers = {"Access-Control-Request-Method": "POST"}
    ok = client.options("/api/v1/attempts", headers={**headers, "Origin": "http://localhost:5173"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    other = client.options("/api/v1/attempts", headers={**headers, "Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_media_serves_song_files(client):
    r = client.get("/media/songs/demo/song.json")
    assert r.status_code == 200
    assert r.json()["id"] == "demo"


# --- boundaries -----------------------------------------------------------------


def test_tiny_upload_is_no_speech_not_an_error(client):
    r = post(client, LINE_FORM, audio=("take.webm", b"\0" * 100, "audio/webm"))
    assert r.status_code == 200
    assert r.json()["status"] == "no_speech"


def test_mode_is_ignored_for_word_target(client):
    r = post(client, {**WORD_FORM, "mode": "rap"})
    assert r.status_code == 200, r.text
    assert r.json()["mode"] is None


def test_word_index_is_ignored_for_line_target(client):
    r = post(client, {**LINE_FORM, "word_index": "99"})
    assert r.status_code == 200, r.text
    assert r.json()["word_index"] is None


# --- failures -------------------------------------------------------------------


@pytest.mark.parametrize("path, code", [
    ("/api/v1/songs/nope", "song_not_found"),
    ("/api/v1/nothing-here", "not_found"),
])
def test_get_not_found(client, path, code):
    assert_error(client.get(path), 404, code)


@pytest.mark.parametrize("form, code", [
    ({**LINE_FORM, "song_id": "nope"}, "song_not_found"),
    ({**LINE_FORM, "line_index": "2"}, "line_not_found"),
    ({**LINE_FORM, "line_index": "-1"}, "line_not_found"),
    ({**WORD_FORM, "word_index": "4"}, "word_not_found"),
])
def test_attempt_not_found(client, form, code):
    assert_error(post(client, form), 404, code)


@pytest.mark.parametrize("form, audio", [
    (LINE_FORM, None),
    ({k: v for k, v in LINE_FORM.items() if k != "mode"}, AUDIO),
    ({k: v for k, v in WORD_FORM.items() if k != "word_index"}, AUDIO),
    ({k: v for k, v in LINE_FORM.items() if k != "song_id"}, AUDIO),
    ({**LINE_FORM, "target": "song"}, AUDIO),
    ({**LINE_FORM, "mode": "rap"}, AUDIO),
    ({**LINE_FORM, "line_index": "abc"}, AUDIO),
], ids=["no-audio", "line-no-mode", "word-no-index", "no-song-id", "bad-target", "bad-mode", "bad-line-index"])
def test_attempt_bad_request(client, form, audio):
    assert_error(post(client, form, audio=audio), 422, "bad_request")


def test_real_grader_bad_audio(client, monkeypatch):
    monkeypatch.setenv("GRADER", "real")

    def reject(data):
        raise BadAudio("not a recording")

    monkeypatch.setattr(main, "load_audio", reject)
    assert_error(post(client, LINE_FORM), 422, "bad_audio")


def silent_wav(seconds: float) -> tuple[str, bytes, str]:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\0\0" * int(16000 * seconds))
    return ("take.wav", buf.getvalue(), "audio/wav")


def test_real_grader_rejects_long_recording(client, monkeypatch):
    monkeypatch.setenv("GRADER", "real")
    assert_error(post(client, LINE_FORM, audio=silent_wav(31)), 413, "audio_too_long")


def test_real_grader_undecodable_upload_is_bad_audio(client, monkeypatch):
    monkeypatch.setenv("GRADER", "real")
    assert_error(post(client, LINE_FORM), 422, "bad_audio")


def test_real_grader_failure_is_grading_failed(client, monkeypatch):
    monkeypatch.setenv("GRADER", "real")

    def explode(*args):
        raise RuntimeError("layer bug")

    monkeypatch.setattr(main, "grade", explode)
    assert_error(post(client, LINE_FORM, audio=silent_wav(1)), 500, "grading_failed")


# --- saved attempts --------------------------------------------------------------


def fake_result(status="ok") -> AttemptResult:
    return AttemptResult(
        attempt_id="", song_id="", line_index=0, word_index=None, target="line", mode="spoken",
        status=status, engine="whisper",
        scores=Scores(overall=None, pronunciation=None, completeness=None, rhythm=None, tone=None, melody=None),
        words=[], syllables=[], heard=None, next_step=LineStep(type="retry_line", message="again"),
    )


def tone_wav(seconds: float, amplitude: float = 0.5) -> tuple[str, bytes, str]:
    t = np.arange(int(16000 * seconds)) / 16000
    pcm = (amplitude * np.sin(2 * np.pi * 220 * t) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm.tobytes())
    return ("take.wav", buf.getvalue(), "audio/wav")


@pytest.mark.parametrize("form", [LINE_FORM, WORD_FORM], ids=["line", "word"])
def test_real_retries_grade_each_upload_instead_of_reusing_the_previous_result(client, monkeypatch, saved, form):
    monkeypatch.setenv("GRADER", "real")
    for flag in main.config.LAYER_FLAGS:
        monkeypatch.setenv(flag, "0")
    line = songs.get_line(songs.get_song("demo"), 0)
    expected_text = line.text if form["target"] == "line" else songs.get_word(line, int(form["word_index"])).text
    inputs = []

    # Replace only the model. Exercise upload decoding, transcription cleanup,
    # syllable matching, scoring and saving on four takes of the same target.
    def transcribe(samples, **kwargs):
        inputs.append(samples.copy())
        peak = float(np.max(np.abs(samples)))
        text = expected_text if peak < 0.3 else "aaaa" if peak < 0.6 else "啊啊"
        return iter([SimpleNamespace(text=text)]), None

    monkeypatch.setattr(tr, "load_model", lambda: SimpleNamespace(transcribe=transcribe))
    responses = [post(client, form, audio=tone_wav(1, amplitude)) for amplitude in (0.2, 0.5, 0.8, 0.2)]
    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    good, empty, wrong, recovered = [r.json() for r in responses]
    assert good["scores"]["overall"] == 100
    assert empty["status"] == "no_speech"
    assert all(score is None for score in empty["scores"].values())
    assert empty["words"] == [] and empty["heard"] is None
    assert wrong["heard"]["hanzi"] == "啊啊"
    assert wrong["scores"]["overall"] < good["scores"]["overall"]
    assert recovered["scores"] == good["scores"]
    assert len({r.json()["attempt_id"] for r in responses}) == 4
    assert all(r.json()["engine"] == "whisper" for r in responses)
    assert len(inputs) == 4
    assert not np.array_equal(inputs[0], inputs[1])
    assert not np.array_equal(inputs[1], inputs[2])
    assert np.array_equal(inputs[0], inputs[3])
    assert len(list(saved.glob("*.wav"))) == 4


@pytest.mark.parametrize("status", ["ok", "no_speech"])
def test_real_attempt_is_saved_as_wav_and_json(client, monkeypatch, saved, status):
    monkeypatch.setenv("GRADER", "real")
    monkeypatch.setattr(main, "grade", lambda *args: fake_result(status))
    r = post(client, LINE_FORM, audio=tone_wav(1))
    assert r.status_code == 200, r.text
    body = r.json()
    attempt_id = body["attempt_id"]
    assert re.fullmatch(r"att_[0-9a-f]{12}", attempt_id)
    assert body["song_id"] == "demo"
    assert sorted(p.name for p in saved.iterdir()) == [f"{attempt_id}.json", f"{attempt_id}.wav"]

    record = json.loads((saved / f"{attempt_id}.json").read_text(encoding="utf-8"))
    assert record["result"] == body
    assert record["trim_offset_ms"] == 0
    with wave.open(str(saved / f"{attempt_id}.wav")) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (1, 2, 16000, 16000)


def test_mock_attempt_is_not_saved(client, saved):
    assert post(client, LINE_FORM).status_code == 200
    assert not saved.exists()


def test_undecodable_upload_is_not_saved(client, monkeypatch, saved):
    monkeypatch.setenv("GRADER", "real")
    assert_error(post(client, LINE_FORM), 422, "bad_audio")
    assert not saved.exists()


def test_grading_failure_is_not_saved(client, monkeypatch, saved):
    monkeypatch.setenv("GRADER", "real")
    monkeypatch.setattr(main, "grade", lambda *args: (_ for _ in ()).throw(RuntimeError("bug")))
    assert_error(post(client, LINE_FORM, audio=tone_wav(1)), 500, "grading_failed")
    assert not saved.exists()


def test_save_failure_still_returns_the_grade(client, monkeypatch, tmp_path):
    monkeypatch.setenv("GRADER", "real")
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("x")
    monkeypatch.setattr(attempts, "ATTEMPTS_DIR", blocker)
    monkeypatch.setattr(main, "grade", lambda *args: fake_result())
    r = post(client, LINE_FORM, audio=tone_wav(1))
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_saved_wav_clips_out_of_range_samples(tmp_path):
    from app.schemas import Audio
    audio = Audio(samples=np.array([-2.0, -1.0, 0.0, 0.5, 2.0], dtype=np.float32), sample_rate=16000, trim_offset_ms=0)
    attempts.write_wav(tmp_path / "x.wav", audio)
    with wave.open(str(tmp_path / "x.wav")) as w:
        values = np.frombuffer(w.readframes(5), dtype="<i2").tolist()
    assert values == [-32767, -32767, 0, 16383, 32767]


def test_media_does_not_expose_attempts(client):
    assert client.get("/media/attempts/.gitkeep").status_code == 404
    assert client.get("/media/songs/../attempts/.gitkeep").status_code == 404


def test_bad_grader_value_rejected(monkeypatch):
    monkeypatch.setenv("GRADER", "fake")
    with pytest.raises(ValueError):
        main.config.grader()


# --- startup --------------------------------------------------------------------


@pytest.mark.parametrize(("grader", "loads"), [("real", 1), ("mock", 0)])
def test_whisper_loaded_at_startup_only_for_real_grader(monkeypatch, grader, loads):
    calls = []
    monkeypatch.setattr(main, "warmup", lambda: calls.append(1))
    monkeypatch.setenv("GRADER", grader)
    with TestClient(main.app) as c:
        assert len(calls) == loads
        assert c.get("/api/v1/health").status_code == 200
    assert len(calls) == loads
