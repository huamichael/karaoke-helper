"""Tests for the HTTP routes, run against the mock grader.

Checks response shapes and the error codes in docs/contracts/api.md.

Owner: B.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app import main, songs
from app.audio import BadAudio
from app.schemas import AttemptResult, ErrorBody

AUDIO = ("take.webm", b"\0" * 4096, "audio/webm")
LINE_FORM = {"song_id": "demo", "line_index": "0", "target": "line", "mode": "spoken"}
WORD_FORM = {"song_id": "demo", "line_index": "0", "target": "word", "word_index": "3"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GRADER", "mock")
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


def test_real_grader_failure_is_grading_failed(client, monkeypatch):
    monkeypatch.setenv("GRADER", "real")
    assert_error(post(client, LINE_FORM), 500, "grading_failed")


def test_media_does_not_expose_attempts(client):
    assert client.get("/media/attempts/.gitkeep").status_code == 404
    assert client.get("/media/songs/../attempts/.gitkeep").status_code == 404


def test_bad_grader_value_rejected(monkeypatch):
    monkeypatch.setenv("GRADER", "fake")
    with pytest.raises(ValueError):
        main.config.grader()
