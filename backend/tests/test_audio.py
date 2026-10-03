"""Tests for load_audio in app/audio.py.

Recordings are synthesised in memory (WAV with the standard library, webm/opus
with PyAV), so the expected trim points are known exactly.

Owner: B.
"""

import io
import wave

import av
import numpy as np
import pytest

from app.audio import AudioTooLong, BadAudio, load_audio

SR = 16000


def tone(seconds: float, rate: int = SR, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(round(seconds * rate))) / rate
    return (amp * np.sin(2 * np.pi * 440 * t)).astype(np.float32)


def silence(seconds: float, rate: int = SR) -> np.ndarray:
    return np.zeros(int(round(seconds * rate)), dtype=np.float32)


def wav(samples: np.ndarray, rate: int = SR, channels: int = 1) -> bytes:
    pcm = (samples * 32767).astype(np.int16)
    if channels == 2:
        pcm = np.repeat(pcm, 2)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def webm_opus(samples: np.ndarray, rate: int = 48000) -> bytes:
    buf = io.BytesIO()
    with av.open(buf, mode="w", format="webm") as out:
        stream = out.add_stream("libopus", rate=rate, layout="mono")
        frame = av.AudioFrame.from_ndarray((samples * 32767).astype(np.int16).reshape(1, -1), format="s16",
                                           layout="mono")
        frame.sample_rate = rate
        for packet in stream.encode(frame):
            out.mux(packet)
        for packet in stream.encode(None):
            out.mux(packet)
    return buf.getvalue()


PADDED = np.concatenate([silence(0.5), tone(1.0), silence(0.5)])


# --- happy path ---------------------------------------------------------------


def test_trims_silence_keeping_150ms_margin():
    audio = load_audio(wav(PADDED))
    assert audio.sample_rate == SR
    assert audio.samples.dtype == np.float32
    assert audio.trim_offset_ms == 350
    assert len(audio.samples) == int(1.3 * SR)
    assert float(np.abs(audio.samples).max()) <= 1.0


def test_resamples_44k_stereo_to_16k_mono():
    rate = 44100
    padded = np.concatenate([silence(0.5, rate), tone(1.0, rate), silence(0.5, rate)])
    audio = load_audio(wav(padded, rate=rate, channels=2))
    assert audio.samples.ndim == 1
    assert audio.sample_rate == SR
    assert abs(audio.trim_offset_ms - 350) <= 20
    assert abs(len(audio.samples) / SR - 1.3) <= 0.04


def test_decodes_webm_opus_like_the_browser_sends():
    rate = 48000
    padded = np.concatenate([silence(0.5, rate), tone(1.0, rate), silence(0.5, rate)])
    audio = load_audio(webm_opus(padded, rate))
    assert audio.sample_rate == SR and audio.samples.ndim == 1
    assert abs(audio.trim_offset_ms - 350) <= 40
    assert abs(len(audio.samples) / SR - 1.3) <= 0.08


# --- boundaries -----------------------------------------------------------------


def test_no_leading_silence_gives_zero_offset():
    audio = load_audio(wav(np.concatenate([tone(1.0), silence(0.5)])))
    assert audio.trim_offset_ms == 0
    assert len(audio.samples) == int(1.15 * SR)


def test_all_silence_is_returned_untrimmed():
    audio = load_audio(wav(silence(1.0)))
    assert audio.trim_offset_ms == 0
    assert len(audio.samples) == SR


def test_exactly_30_seconds_is_accepted():
    assert len(load_audio(wav(silence(30.0))).samples) == 30 * SR


def test_over_30_seconds_is_rejected():
    with pytest.raises(AudioTooLong):
        load_audio(wav(silence(30.1)))


def test_audio_too_long_is_bad_audio():
    assert issubclass(AudioTooLong, BadAudio)


# --- failures -------------------------------------------------------------------


@pytest.mark.parametrize("data", [
    b"",
    np.random.default_rng(0).bytes(5000),
    wav(tone(1.0))[:30],
], ids=["empty", "random-bytes", "truncated-header"])
def test_undecodable_bytes_raise_bad_audio(data):
    with pytest.raises(BadAudio):
        load_audio(data)
