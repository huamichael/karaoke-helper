"""FastAPI application and routes.

Serves the song list, a song bundle, and POST /api/v1/attempts, which hands a
recording to the grader and returns an AttemptResult. Also mounts /media and
enables CORS for the frontend dev server. Contains no grading logic.

Owner: B. Spec: docs/contracts/api.md.
"""

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import config, songs
from app.audio import AudioTooLong, BadAudio, load_audio
from app.schemas import AttemptResult, ErrorBody, ErrorDetail, Health, Song, SongSummary
from app.scoring.grader import grade
from app.scoring.mock import grade_mock
from app.scoring.transcribe import warmup

log = logging.getLogger(__name__)

config.grader()  # fail at startup on a bad GRADER value
config.whisper_engine()
config.validate_layer_flags()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if config.grader() == "real":
        warmup()
    yield


app = FastAPI(title="Karaoke_Helper API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/media/songs", StaticFiles(directory=songs.SONGS_DIR, check_dir=False), name="media-songs")

ERRORS = {code: {"model": ErrorBody} for code in (404, 413, 422, 500)}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _error(status: int, code: str, message: str) -> JSONResponse:
    body = ErrorBody(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status, content=body.model_dump())


@app.exception_handler(ApiError)
async def _api_error(_: Request, e: ApiError) -> JSONResponse:
    return _error(e.status, e.code, e.message)


@app.exception_handler(songs.NotFound)
async def _not_found(_: Request, e: songs.NotFound) -> JSONResponse:
    return _error(404, e.code, str(e))


@app.exception_handler(RequestValidationError)
async def _bad_request(_: Request, e: RequestValidationError) -> JSONResponse:
    details = "; ".join(f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors())
    return _error(422, "bad_request", details)


@app.exception_handler(StarletteHTTPException)
async def _http_error(_: Request, e: StarletteHTTPException) -> JSONResponse:
    return _error(e.status_code, "not_found" if e.status_code == 404 else "http_error", str(e.detail))


@app.get("/api/v1/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", grader=config.grader())


@app.get("/api/v1/songs", response_model=list[SongSummary])
def list_songs() -> list[SongSummary]:
    return songs.list_songs()


@app.get("/api/v1/songs/{song_id}", response_model=Song, responses=ERRORS)
def get_song(song_id: str) -> Song:
    return songs.get_song(song_id)


@app.post("/api/v1/attempts", response_model=AttemptResult, responses=ERRORS)
async def create_attempt(
    audio: Annotated[UploadFile, File()],
    song_id: Annotated[str, Form()],
    line_index: Annotated[int, Form()],
    target: Annotated[Literal["line", "word"], Form()],
    mode: Annotated[str | None, Form(description="'spoken' or 'singing'; required for line, ignored for word")] = None,
    word_index: Annotated[int | None, Form()] = None,
) -> AttemptResult:
    if target == "line":
        if mode not in ("spoken", "singing"):
            raise ApiError(422, "bad_request", "mode must be 'spoken' or 'singing' when target is 'line'")
        word_index = None
    else:
        if word_index is None:
            raise ApiError(422, "bad_request", "word_index is required when target is 'word'")
        mode = None

    line = songs.get_line(songs.get_song(song_id), line_index)
    if word_index is not None:
        songs.get_word(line, word_index)

    data = await audio.read()
    attempt_id = f"att_{uuid.uuid4().hex[:12]}"
    try:
        if config.grader() == "mock":
            return grade_mock(data, song_id, line, target, mode, word_index, attempt_id)
        result = grade(load_audio(data), line, target, mode, word_index)
        return result.model_copy(update={"attempt_id": attempt_id, "song_id": song_id})
    except AudioTooLong as e:
        raise ApiError(413, "audio_too_long", str(e)) from e
    except BadAudio as e:
        raise ApiError(422, "bad_audio", str(e) or "The recording could not be decoded.") from e
    except Exception as e:
        log.exception("grading failed for %s", attempt_id)
        raise ApiError(500, "grading_failed", "Something went wrong while grading. Try again.") from e
