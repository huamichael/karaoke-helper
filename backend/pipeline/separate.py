"""Split a song's track into the singer's voice and the instrumental, with Demucs.

Used by line_ends, which needs the voice, and instrumental, which needs the rest.
Demucs is in the optional uv group "vocals", so run those tools with
`uv run --group vocals ...`. One separation takes a minute or a few on CPU.

Owner: D. Spec: docs/tasks/backend-songs-tone.md ("Instrumentals").
"""

from __future__ import annotations

import sys
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

VOICE_RATE = 16_000  # check/vocals.wav, as line_ends reads it


@dataclass
class Stems:
    voice: np.ndarray         # the singer alone: float32, mono, VOICE_RATE
    instrumental: np.ndarray  # everything else: float32, stereo, shape (2, n), at rate
    rate: int                 # the instrumental's sample rate


def separate(folder: Path) -> Stems:
    """Separate folder/audio.mp3. The instrumental is every source but the voice, as long as the track."""
    try:
        import torch
        from demucs.apply import apply_model
        from demucs.audio import convert_audio
        from demucs.pretrained import get_model
    except ImportError:
        sys.exit("Demucs is not installed. Run the tool with:  uv run --group vocals python -m pipeline.<tool> ...")

    import av

    print(f"{folder.name}: separating the voice from the track with Demucs (a minute or a few on CPU) ...",
          file=sys.stderr)
    model = get_model("htdemucs").eval()
    chunks = []
    with av.open(str(folder / "audio.mp3")) as container:
        resampler = av.AudioResampler(format="fltp", layout="stereo", rate=model.samplerate)
        for frame in container.decode(audio=0):
            chunks.extend(out.to_ndarray() for out in resampler.resample(frame))
        chunks.extend(out.to_ndarray() for out in resampler.resample(None))
    track = torch.from_numpy(np.concatenate(chunks, axis=1))

    # Normalise as the demucs command does, so the instrumental comes back at the track's own level.
    ref = track.mean(0)
    mean, std = ref.mean(), ref.std() + 1e-8
    with torch.no_grad():
        sources = apply_model(model, ((track - mean) / std)[None], device="cpu", progress=True)[0]
    sources = sources * std + mean

    voice = model.sources.index("vocals")
    rest = [k for k in range(len(model.sources)) if k != voice]
    return Stems(
        voice=convert_audio(sources[voice], model.samplerate, VOICE_RATE, 1)[0].numpy().astype(np.float32),
        instrumental=sources[rest].sum(0).numpy().astype(np.float32),
        rate=model.samplerate,
    )


def save_voice(folder: Path, voice: np.ndarray) -> None:
    """Keep the voice as check/vocals.wav (16-bit, mono, VOICE_RATE), which git ignores."""
    cached = folder / "check" / "vocals.wav"
    cached.parent.mkdir(exist_ok=True)
    with wave.open(str(cached), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(VOICE_RATE)
        w.writeframes((np.clip(voice, -1, 1) * 32767).astype("<i2").tobytes())
