"""Tests for the karaoke track tool (pipeline/instrumental.py) and build_song's instrumental_url.

Demucs itself is not run here: it is an optional dependency and takes minutes.
"""

import av
import numpy as np
import yaml

from pipeline import instrumental
from pipeline.build_song import build_song, write_song

LYRICS = {
    "metadata": {"title": "Test", "artist": "Nobody"},
    "lines": [{"text": "我想和你一起", "start_ms": 1000, "end_ms": 4000}, {"text": "", "start_ms": 4000}],
}


def song_folder(tmp_path):
    folder = tmp_path / "test-song"
    folder.mkdir()
    (folder / "lyrics.yaml").write_text(yaml.safe_dump(LYRICS, allow_unicode=True), encoding="utf-8")
    return folder


def test_build_song_links_the_instrumental_only_when_it_exists(tmp_path):
    folder = song_folder(tmp_path)
    assert build_song(folder, make_clips=False).instrumental_url is None
    (folder / "instrumental.mp3").write_bytes(b"")
    assert build_song(folder, make_clips=False).instrumental_url == "/media/songs/test-song/instrumental.mp3"


def test_link_updates_song_json(tmp_path):
    folder = song_folder(tmp_path)
    write_song(folder, build_song(folder, make_clips=False))
    (folder / "instrumental.mp3").write_bytes(b"")
    instrumental.link(folder)
    assert '"instrumental_url": "/media/songs/test-song/instrumental.mp3"' in (folder / "song.json").read_text()
    (folder / "instrumental.mp3").unlink()
    instrumental.link(folder)
    assert '"instrumental_url": null' in (folder / "song.json").read_text()


def test_write_mp3_round_trip(tmp_path):
    rate, seconds = 44_100, 1.5
    t = np.arange(int(rate * seconds)) / rate
    stereo = np.stack([0.5 * np.sin(2 * np.pi * 440 * t), 0.5 * np.sin(2 * np.pi * 660 * t)]).astype(np.float32)
    path = tmp_path / "instrumental.mp3"
    instrumental.write_mp3(path, stereo, rate)
    assert not (tmp_path / "instrumental.part.mp3").exists()

    with av.open(str(path)) as container:
        frames = [f.to_ndarray() for f in container.decode(audio=0)]
        assert container.streams.audio[0].channels == 2
    decoded = np.concatenate(frames, axis=1)
    assert abs(decoded.shape[1] / rate - seconds) < 0.1  # the encoder adds a few ms of padding at most
    assert 0.3 < np.abs(decoded).max() < 0.6
