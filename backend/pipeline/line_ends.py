"""Line timing: start each line with its singing, and trim lines that run long.

Command-line tool, two modes.

1. Report (the default) prints, for each line, where the voice falls silent and a
   suggested end_ms. It changes nothing:

    uv run --group vocals python -m pipeline.line_ends --song yi-jian-mei

2. --apply corrects line times in lyrics.yaml, then rebuilds song.json. It moves a
   line's start to START_LEAD_MS before its first aligned syllable whenever the
   singing begins before the line does, and ends the line before it there, so no
   line clips its first word or plays the start of the next line. Lyric timestamps
   are often 0.1-0.2 s late. This needs only the syllable times from align_track.
   Add --trim-fades to also cut lines before an instrumental break where the voice
   has stopped (uses Demucs and --silence-db, as the report does).

    uv run python -m pipeline.line_ends --song yi-jian-mei --apply

The first run separates the singer's voice from the track with Demucs (a minute or
two on CPU) and keeps it as data/songs/<id>/check/vocals.wav, which git ignores
because it is cut from a copyrighted track. Later runs reuse it.

For each line it prints the current end_ms, where the voice falls silent, and a
suggested end_ms: the voice end plus TAIL_MS, never later than the current end.
Ballads end lines on long fading notes; --silence-db sets where in the fade the
voice counts as stopped (30 keeps the whole fade, 15 cuts once it has faded).
To trim a line, copy its suggestion into that line's end_ms in lyrics.yaml (find
it by start_ms), then rebuild with build_song. Aligned syllable times are kept.

Owner: D. Spec: docs/tasks/backend-songs-tone.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path

import numpy as np

SONGS_DIR = Path(__file__).resolve().parents[2] / "data" / "songs"
RATE = 16_000
FRAME_MS = 20
TAIL_MS = 300          # keep this much after the voice stops, so the last sound is not clipped
START_LEAD_MS = 150    # without the voice track: start a line this long before its first aligned syllable
ONSET_LEAD_MS = 100    # with it: start a line after a break this long before the voice comes in
ONSET_DB = 10          # the voice "comes in" when it rises to within this of the line's loudest moment;
                       # instruments leaking into the voice track stay 17-20 dB below it
SEARCH_MS = 1_500      # look this far either side of a boundary for the singer's breath
ONSET_SEARCH_MS = 800  # after a break, look this far before the first aligned syllable for the voice coming in
SILENT_DB = 20         # default: the voice counts as stopped this far below the line's loudest moment
FLAG_MS = 1_000        # lines with more trailing time than this are worth trimming


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report where the singing stops in each line.")
    parser.add_argument("--song", required=True, help="song folder name under data/songs/")
    parser.add_argument("--silence-db", type=float, default=SILENT_DB,
                        help="how far (dB) below the line's loudest moment the voice counts as stopped. "
                             "Ballads end on long fading notes: 30 keeps the whole fade, 15 cuts once it has "
                             f"faded noticeably (default {SILENT_DB:g})")
    parser.add_argument("--apply", action="store_true",
                        help="correct line starts (and ends) in lyrics.yaml from the aligned syllables, then rebuild")
    parser.add_argument("--trim-fades", action="store_true",
                        help="with --apply: also trim lines before an instrumental break where the voice has stopped")
    args = parser.parse_args(argv)

    folder = SONGS_DIR / args.song
    song = json.loads((folder / "song.json").read_text(encoding="utf-8"))
    if args.apply:
        return apply(folder, song, args.silence_db if args.trim_fades else None)
    vocals = load_vocals(folder)

    print(f"{song['title']} ({song['id']}), voice counts as stopped {args.silence_db:g} dB below its peak")
    print(f"{'line':>4}  {'start_ms':>8}  {'end_ms':>7}  {'voice ends':>10}  {'suggested':>9}  {'trailing':>8}  text")
    flagged = 0
    for line in song["lines"]:
        voice_end = singing_end(vocals, line["start_ms"], line["end_ms"], args.silence_db)
        if voice_end is None:
            print(f"{line['index']:>4}  {line['start_ms']:>8}  {line['end_ms']:>7}  {'no voice':>10}  {'-':>9}  {'-':>8}  {line['text']}")
            continue
        suggested = min(line["end_ms"], round_to(voice_end + TAIL_MS, 10))
        trailing = line["end_ms"] - voice_end
        mark = "  <- trim?" if trailing > FLAG_MS else ""
        flagged += trailing > FLAG_MS
        print(f"{line['index']:>4}  {line['start_ms']:>8}  {line['end_ms']:>7}  {voice_end:>10}  {suggested:>9}  "
              f"{trailing / 1000:>7.1f}s  {line['text']}{mark}")
    print(f"\n{flagged} line(s) run more than {FLAG_MS / 1000:.0f} s past the singing. Listen to check/<line>.wav "
          "(build_song --check) before trusting a suggestion: quiet endings and breaths can fool it.")
    return 0


def apply(folder: Path, song: dict, silence_db: float | None) -> int:
    """Rewrite line times in lyrics.yaml, print what changed, and rebuild song.json."""
    import yaml

    from pipeline.build_song import build_song, write_song

    path = folder / "lyrics.yaml"
    text = path.read_text(encoding="utf-8")
    entries = yaml.safe_load(text)["lines"]
    trims = None
    if silence_db is not None:
        vocals = load_vocals(folder)
        trims = {}
        for line in song["lines"]:
            end = singing_end(vocals, line["start_ms"], line["end_ms"], silence_db)
            if end is not None and line["end_ms"] - end > FLAG_MS:
                trims[line["index"]] = round_to(end + TAIL_MS, 10)

    voice = vocals_if_available(folder)
    if voice is None:
        print("warning: no voice track (run with --group vocals once to make check/vocals.wav); "
              "using the aligned syllable times only, which can run 0.1-0.3 s late", file=sys.stderr)
    times = corrected_times(entries, song["lines"], trims, voice)
    changed = 0
    print(f"{song['title']} ({song['id']}): line times in lyrics.yaml")
    for entry, (start, end) in zip(entries, times):
        if (start, end) != (entry["start_ms"], entry.get("end_ms")):
            changed += 1
            label = entry["text"] or "(instrumental)"
            print(f"  {entry['start_ms']:>7}-{entry.get('end_ms') or '':<7} -> {start:>7}-{end or '':<7}  {label}")
    if not changed:
        print("  nothing to change")
        return 0
    path.write_text(rewrite_times(text, times), encoding="utf-8")
    write_song(folder, build_song(folder, make_clips=False))
    print(f"{changed} entr{'y' if changed == 1 else 'ies'} changed. Rebuilt {folder / 'song.json'}; syllable times kept.")
    return 0


def corrected_times(entries: list[dict], song_lines: list[dict], trims: dict[int, int] | None = None,
                    vocals: np.ndarray | None = None) -> list[tuple[int, int | None]]:
    """New (start_ms, end_ms) for every lyrics.yaml entry, instrumental gaps included, in order.

    song_lines are song.json's lines, which are the entries with text, in the same order.

    With the singer's voice track (vocals, 16 kHz), a boundary between two sung lines moves to
    the quietest moment of the voice between the first line's last syllable and the second's
    first: the breath, so neither line clips the other. A line after an instrumental break
    starts ONSET_LEAD_MS before the voice comes in. Without the voice track, a line starts
    START_LEAD_MS before its first aligned syllable; the aligner can run late, so this is rougher.
    """
    starts = [e["start_ms"] for e in entries]
    ends = [e.get("end_ms") for e in entries]
    lyric = [k for k, e in enumerate(entries) if e["text"].strip()]
    previous_last = None
    for n, (k, line) in enumerate(zip(lyric, song_lines)):
        sung = [s["start_ms"] for s in line["syllables"] if s["start_ms"] is not None]
        follows_line = n > 0 and lyric[n - 1] == k - 1  # sung straight after the previous line
        if vocals is not None:
            first = sung[0] if sung else starts[k] + 400
            if follows_line:
                # Between the previous line's last syllable and this line's first, whatever the
                # current boundary is, so running the tool again changes nothing.
                hi = first
                lo = max(hi - SEARCH_MS, (previous_last or entries[k - 1]["start_ms"]) + 300)
                if hi > lo:
                    starts[k] = quietest_ms(vocals, lo, hi)
            else:
                # Search near the first aligned syllable (the aligner is at most a few hundred ms late),
                # not near the current start, which may be wrong: intros can be loud in the voice track.
                onset = voice_onset_ms(vocals, max(0, first - ONSET_SEARCH_MS), first + 200, ends[k] or first + 2000)
                if onset is not None:
                    starts[k] = max(0, min(onset - ONSET_LEAD_MS, first - 50))
        elif sung:
            earliest = sung[0] - START_LEAD_MS
            if previous_last is not None:
                earliest = max(earliest, previous_last + START_LEAD_MS)  # never swallow the previous line's singing
            starts[k] = max(0, min(starts[k], earliest))
        if follows_line:
            ends[k - 1] = starts[k]
        if sung:
            previous_last = sung[-1]
        if trims and line["index"] in trims:
            following = entries[k + 1] if k + 1 < len(entries) else None
            if following is None or not following["text"].strip():
                ends[k] = max(starts[k] + 1, min(ends[k], trims[line["index"]]))
    for k in range(len(entries) - 1):
        if ends[k] is not None and ends[k] > starts[k + 1]:
            ends[k] = starts[k + 1]
    return list(zip(starts, ends))


def _envelope(vocals: np.ndarray, lo: int, hi: int) -> np.ndarray:
    """The voice's level (RMS) every FRAME_MS from lo to hi ms, smoothed over three frames."""
    frame = RATE * FRAME_MS // 1000
    segment = vocals[max(0, lo) * RATE // 1000: max(0, hi) * RATE // 1000]
    count = len(segment) // frame
    if count == 0:
        return np.zeros(0)
    rms = np.sqrt(np.mean(segment[: count * frame].reshape(count, frame) ** 2, axis=1))
    return np.convolve(rms, np.ones(3) / 3, mode="same")


def quietest_ms(vocals: np.ndarray, lo: int, hi: int) -> int:
    """Track time (ms, a multiple of 10) of the voice's quietest moment between lo and hi."""
    level = _envelope(vocals, lo, hi)
    if level.size == 0:
        return lo
    return round_to(lo + int(np.argmin(level)) * FRAME_MS + FRAME_MS // 2, 10)


def voice_onset_ms(vocals: np.ndarray, lo: int, hi: int, line_end: int) -> int | None:
    """Where the voice comes in between lo and hi: the start of its rise to within ONSET_DB of the line's peak."""
    peak = float(_envelope(vocals, lo, line_end).max(initial=0.0))
    level = _envelope(vocals, lo, hi)
    if peak < 1e-4 or level.size == 0:
        return None
    loud = np.flatnonzero(level > peak * 10 ** (-ONSET_DB / 20))
    if not loud.size:
        return None
    i = int(loud[0])
    while i > 0 and level[i - 1] < level[i]:  # step back to where the rise began
        i -= 1
    return lo + i * FRAME_MS


def vocals_if_available(folder: Path) -> np.ndarray | None:
    """The cached voice track, or a fresh one if Demucs is installed; None if neither."""
    if (folder / "check" / "vocals.wav").exists():
        return load_vocals(folder)
    try:
        import demucs  # noqa: F401
    except ImportError:
        return None
    return load_vocals(folder)


def rewrite_times(text: str, times: list[tuple[int, int | None]]) -> str:
    """lyrics.yaml with each line entry's start_ms and end_ms replaced, everything else untouched."""
    out, entry, in_lines = [], -1, False
    for raw in text.splitlines(keepends=True):
        stripped = raw.strip()
        if raw.startswith("lines:"):
            in_lines = True
        elif in_lines and raw[:1] not in (" ", "-", "\n", "\r", "#") and stripped:
            in_lines = False  # the next top-level key
        elif in_lines and raw.startswith("- "):
            entry += 1
        if in_lines and entry >= 0 and stripped.startswith(("start_ms:", "end_ms:")):
            key = stripped.split(":", 1)[0]
            value = times[entry][0] if key == "start_ms" else times[entry][1]
            if value is not None:
                raw = f"{raw[: len(raw) - len(raw.lstrip())]}{key}: {value}\n"
        out.append(raw)
    return "".join(out)


def load_vocals(folder: Path) -> np.ndarray:
    """The singer's voice alone, 16 kHz mono, separated once and cached in check/vocals.wav."""
    cached = folder / "check" / "vocals.wav"
    if cached.exists():
        with wave.open(str(cached)) as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
    try:
        import torch
        from demucs.apply import apply_model
        from demucs.audio import convert_audio
        from demucs.pretrained import get_model
    except ImportError:
        sys.exit("Demucs is not installed. Run with:  uv run --group vocals python -m pipeline.line_ends --song <id>")

    import av

    print("separating the singer's voice with Demucs (once per song, a minute or two) ...", file=sys.stderr)
    model = get_model("htdemucs").eval()
    chunks = []
    with av.open(str(folder / "audio.mp3")) as container:
        resampler = av.AudioResampler(format="fltp", layout="stereo", rate=model.samplerate)
        for frame in container.decode(audio=0):
            chunks.extend(out.to_ndarray() for out in resampler.resample(frame))
        chunks.extend(out.to_ndarray() for out in resampler.resample(None))
    track = torch.from_numpy(np.concatenate(chunks, axis=1))
    with torch.no_grad():
        sources = apply_model(model, track[None], device="cpu", progress=True)[0]
    voice = sources[model.sources.index("vocals")]
    voice = convert_audio(voice, model.samplerate, RATE, 1)[0].numpy().astype(np.float32)

    cached.parent.mkdir(exist_ok=True)
    with wave.open(str(cached), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(voice, -1, 1) * 32767).astype("<i2").tobytes())
    return voice


def singing_end(vocals: np.ndarray, start_ms: int, end_ms: int, silence_db: float = SILENT_DB) -> int | None:
    """Track time (ms) where the voice last rises above the silence line inside [start_ms, end_ms]."""
    frame = RATE * FRAME_MS // 1000
    segment = vocals[start_ms * RATE // 1000 : end_ms * RATE // 1000]
    count = len(segment) // frame
    if count == 0:
        return None
    rms = np.sqrt(np.mean(segment[: count * frame].reshape(count, frame) ** 2, axis=1))
    peak = float(rms.max())
    if peak < 1e-4:
        return None
    voiced = np.flatnonzero(rms > peak * 10 ** (-silence_db / 20))
    return start_ms + (int(voiced[-1]) + 1) * FRAME_MS


def round_to(value: float, step: int) -> int:
    return int(round(value / step) * step)


if __name__ == "__main__":
    sys.exit(main())
