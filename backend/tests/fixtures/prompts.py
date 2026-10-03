"""Make a prompt clip for every recording in the session, for people to listen to and copy.

    cd backend && uv run python tests/fixtures/prompts.py

Writes into tests/fixtures/prompts/:
- lines/<line>__sung.wav: the line cut from the original track (copyrighted, ignored by git).
- lines/<line>__<variant>.mp3: the line spoken by a speech voice, with the error or gap if any.
- tone/<reading>__correct.mp3: the word spoken by a speech voice.
- tone/<reading>__said-tone<n>.wav: the same word with its pitch reshaped into another tone.

Needs internet for the speech voice, and data/songs/<song>/audio.mp3 for the sung clips.
Existing prompts are kept; delete one to make it again.

Owner: D. Guide: docs/recording-session.md.
"""

from __future__ import annotations

import asyncio
import json
import sys
import wave
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from session import LINES, WORDS, takes  # noqa: E402

from app.mandarin import to_syllables  # noqa: E402
from app.schemas import Audio  # noqa: E402
from app.scoring.tone import SEMITONES_PER_LEVEL, TONE_SHAPES, score_tones  # noqa: E402

OUT = Path(__file__).resolve().parent / "prompts"
SONGS = BACKEND.parent / "data" / "songs"
VOICE = "zh-CN-XiaoxiaoNeural"
RATE = 16_000


def main() -> int:
    (OUT / "lines").mkdir(parents=True, exist_ok=True)
    (OUT / "tone").mkdir(parents=True, exist_ok=True)

    sung = make_sung_clips()
    # Everything is spoken by the speech voice except sung lines (cut from the
    # track) and wrong-tone words (reshaped from the spoken word).
    spoken = make_speech({
        take_path(t): t.say
        for t in takes()
        if not (t.folder == "audio" and t.variant == "correct") and not t.variant.startswith("said-tone")
    })
    retoned, checks = make_wrong_tones()

    print(f"prompts in {OUT}: {sung} sung lines, {spoken} spoken clips, {retoned} re-toned words")
    for line in checks:
        print(line)
    return 0


def take_path(take) -> Path:
    variant = take.variant
    if take.folder == "audio" and variant == "correct":
        variant = "sung"
    suffix = ".wav" if variant in ("sung",) or variant.startswith("said-tone") else ".mp3"
    folder = "lines" if take.folder == "audio" else "tone"
    return OUT / folder / f"{take.item}__{variant}{suffix}"


def make_sung_clips() -> int:
    """Cut each fixture line out of its song's track: the melody to sing along to."""
    made = 0
    for name, (_, song_id, line_index, _, _) in LINES.items():
        out = OUT / "lines" / f"{name}__sung.wav"
        track = SONGS / song_id / "audio.mp3"
        if out.exists():
            continue
        if not track.exists():
            print(f"warning: {track} is missing; get it from the team share to make {out.name}")
            continue
        song = json.loads((SONGS / song_id / "song.json").read_text(encoding="utf-8"))
        line = song["lines"][line_index]
        samples = decode(track)
        write_wav(out, samples[line["start_ms"] * RATE // 1000 : line["end_ms"] * RATE // 1000])
        made += 1
    return made


def make_speech(clips: dict[Path, str]) -> int:
    """Speak each text with the speech voice. Skips clips that already exist."""
    import edge_tts

    missing = {path: text for path, text in clips.items() if not path.exists()}

    async def run() -> None:
        for path, text in missing.items():
            await edge_tts.Communicate(text, VOICE, rate="-15%").save(str(path))

    asyncio.run(run())
    return len(missing)


def make_wrong_tones() -> tuple[int, list[str]]:
    """Reshape the pitch of each spoken word into the other tones, then check the result."""
    import parselmouth
    from parselmouth.praat import call

    made, checks = 0, []
    for take in takes():
        if not take.variant.startswith("said-tone"):
            continue
        tone = int(take.variant[-1])
        out = take_path(take)
        if not out.exists():
            source = OUT / "tone" / f"{take.item}__correct.mp3"
            sound = parselmouth.Sound(decode(source).astype(np.float64), sampling_frequency=RATE)
            pitch = sound.to_pitch(time_step=0.01, pitch_floor=75, pitch_ceiling=600)
            hertz = pitch.selected_array["frequency"]
            voiced = pitch.xs()[hertz > 0]
            median = float(np.median(hertz[hertz > 0]))

            manipulation = call(sound, "To Manipulation", 0.01, 75, 600)
            tier = call("Create PitchTier", "tone", sound.xmin, sound.xmax)
            for fraction, level in zip(np.linspace(0, 1, len(TONE_SHAPES[tone])), TONE_SHAPES[tone]):
                time = voiced[0] + fraction * (voiced[-1] - voiced[0])
                call(tier, "Add point", time, median * 2 ** ((level - 3) * SEMITONES_PER_LEVEL / 12))
            call([tier, manipulation], "Replace pitch tier")
            result = call(manipulation, "Get resynthesis (overlap-add)")
            write_wav(out, result.values[0].astype(np.float32))
            made += 1

        # The tone grader should hear the tone the prompt was reshaped into.
        grade = score_tones(Audio(decode(out), RATE, 0), to_syllables(WORDS[take.item]), None)[0]
        mark = "ok" if grade.heard == tone else "CHECK BY EAR"
        checks.append(f"  {out.name}: grader hears tone {grade.heard} ({mark})")
    return made, checks


def decode(path: Path) -> np.ndarray:
    """Any audio file as 16 kHz mono float32."""
    import av

    chunks = []
    with av.open(str(path)) as container:
        resampler = av.AudioResampler(format="flt", layout="mono", rate=RATE)
        for frame in container.decode(audio=0):
            chunks.extend(out.to_ndarray().reshape(-1) for out in resampler.resample(frame))
        chunks.extend(out.to_ndarray().reshape(-1) for out in resampler.resample(None))
    return np.concatenate(chunks).astype(np.float32)


def write_wav(path: Path, samples: np.ndarray) -> None:
    """16 kHz mono 16-bit WAV."""
    peak = float(np.max(np.abs(samples))) or 1.0
    scaled = samples / peak * 0.9 if peak > 1.0 else samples
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((np.clip(scaled, -1, 1) * 32767).astype("<i2").tobytes())


if __name__ == "__main__":
    sys.exit(main())
