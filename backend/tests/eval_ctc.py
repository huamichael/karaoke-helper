"""Checkpoint B: compare Whisper and CTC on human recordings (owner C).

Run from backend: uv run python tests/eval_ctc.py [--labels labels.json]
Session names are <line>__<variant>__<speaker>.wav, with indexed errors such
as error-4-l-n. Labels {"filename.wav": [zero_based_error_indices]} also support
legacy error-n-l names when several syllables have initial n. A benchmark and umlaut probe
can use any local recording; they do not establish accuracy on human singing.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
import tempfile
from time import perf_counter
import wave

import numpy as np

# Direct execution (python tests/eval_ctc.py) has tests/, not backend/, on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audio import load_audio
from app.schemas import Audio, Line, SoundScore
from app.scoring import ctc
from app.scoring.matcher import match, score_sounds_base
from app.scoring.transcribe import transcribe
from pipeline.align_track import decode_track
from tests.fixtures.session import parse as parse_session_name

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FLAG_AT = 60  # scoring.md: a confused variant must score at most 60


def error_indices(line: Line, variant: str, annotation: list[int] | None = None) -> set[int]:
    """Resolve labels before any model calls; never infer an ambiguous error."""
    if annotation is not None and (
        not isinstance(annotation, list)
        or any(type(i) is not int or not 0 <= i < len(line.syllables) for i in annotation)
    ):
        raise ValueError("Fixture error labels must be lists of zero-based syllable indices")
    if variant.startswith("missing-"):
        index = variant.removeprefix("missing-")
        if not index.isascii() or not index.isdigit():
            raise ValueError(f"Unsupported missing variant {variant!r}")
        indices = {int(index)}
        if annotation is not None and set(annotation) != indices:
            raise ValueError(f"{variant}: labels contradict the filename")
    elif variant.startswith("error-"):
        fields = variant.split("-")
        indexed = len(fields) == 4 and fields[1].isascii() and fields[1].isdigit()
        if len(fields) != 3 and not indexed:
            raise ValueError(f"Unsupported error variant {variant!r}")
        expected, produced = fields[-2:]
        candidates = {i for i, s in enumerate(line.syllables) if (
            s.initial == expected and produced in ctc.initial_partners(expected)
            or s.final == expected and produced in ctc.final_partners(expected)
        )}
        if indexed:
            indices = {int(fields[1])}
            if not indices <= candidates:
                raise ValueError(f"{variant}: index does not match the expected confused sound")
            if annotation is not None and set(annotation) != indices:
                raise ValueError(f"{variant}: labels contradict the filename")
        elif annotation is None:
            if len(candidates) != 1:
                raise ValueError(f"{variant}: {sorted(candidates)} candidate indices; provide --labels")
            indices = candidates
        else:
            indices = set(annotation)
            if not indices or not indices <= candidates:
                raise ValueError(f"{variant}: labels must select error indices from {sorted(candidates)}")
    elif variant in ("correct", "spoken"):
        if annotation:
            raise ValueError("Correct/spoken recordings cannot carry deliberate-error labels")
        indices = set()
    else:
        raise ValueError(f"Unsupported fixture variant {variant!r}")
    if any(type(i) is not int or not 0 <= i < len(line.syllables) for i in indices):
        raise ValueError("Fixture error indices must be zero-based syllable indices")
    return indices


def recording_name(path: Path) -> tuple[str, str, str]:
    """Read the shared session format, retaining older two-field recordings."""
    parsed = parse_session_name(path.stem)
    if parsed is None:
        fields = path.stem.split("__")
        if len(fields) != 2:
            raise ValueError(f"Fixture name must be <line>__<variant>__<speaker>.wav: {path.name}")
        parsed = (*fields, "legacy")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", parsed[0]):
        raise ValueError(f"Invalid fixture line name: {path.name}")
    return parsed


def validate_wav(path: Path) -> None:
    """Reject broken/session-incompatible audio before loading either model."""
    try:
        with wave.open(str(path), "rb") as handle:
            if (handle.getnchannels(), handle.getsampwidth(), handle.getframerate()) != (1, 2, ctc.SAMPLE_RATE):
                raise ValueError(f"{path.name}: fixtures must be 16 kHz mono PCM16 WAV; use check_recordings.py --convert")
            frames = handle.getnframes()
            if not 0 < frames <= 30 * ctc.SAMPLE_RATE:
                raise ValueError(f"{path.name}: recording must contain audio and be at most 30 seconds")
            if len(handle.readframes(frames)) != frames * 2:
                raise ValueError(f"{path.name}: WAV data is truncated")
    except (wave.Error, EOFError) as exc:
        raise ValueError(f"{path.name}: invalid PCM WAV") from exc


def flagged(sound: SoundScore | None) -> bool:
    return sound is None or any(
        part is not None and part.score is not None and part.score <= FLAG_AT
        for part in (sound.initial, sound.final)
    )


def _components(sound: SoundScore | None) -> str:
    if sound is None:
        return "missing"
    def render(part):
        return "-" if part is None else f"{part.expected}>{part.heard}:{part.score}"
    return f"{render(sound.initial)} {render(sound.final)}"


def export_spans(audio: Audio, spans, folder: Path, stem: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for index, span in enumerate(spans):
        if span is None:
            continue
        samples = audio.samples[span.start_ms * audio.sample_rate // 1000:span.end_ms * audio.sample_rate // 1000]
        with wave.open(str(folder / f"{stem}__{index:02}.wav"), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(audio.sample_rate)
            handle.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())


def benchmark(path: Path, line: Line, runs: int) -> None:
    samples = decode_track(path)
    if len(samples) < 5 * ctc.SAMPLE_RATE:
        raise ValueError("Benchmark recording must contain at least five seconds")
    samples = samples[:5 * ctc.SAMPLE_RATE]
    cold_audio = Audio(samples=samples.copy(), sample_rate=ctc.SAMPLE_RATE, trim_offset_ms=0)
    start = perf_counter()
    spans = ctc.align(cold_audio, line.syllables)
    ctc.score_sounds(cold_audio, line.syllables, spans)
    print(f"cold five-second alignment + scores: {perf_counter() - start:.3f}s (includes model load/download)")
    timings = []
    for _ in range(runs):
        # A fresh Audio identity measures inference, rather than a cache hit.
        audio = Audio(samples=samples.copy(), sample_rate=ctc.SAMPLE_RATE, trim_offset_ms=0)
        start = perf_counter()
        spans = ctc.align(audio, line.syllables)
        ctc.score_sounds(audio, line.syllables, spans)
        timings.append(perf_counter() - start)
    torch, torchaudio, _, _, _ = ctc._runtime()
    print(f"MMS_FA cpu torch={torch.__version__} torchaudio={torchaudio.__version__}; "
          f"warm five-second mean={np.mean(timings):.3f}s ({runs} runs); target ~1s")


def umlaut_probe(path: Path, line: Line, folder: Path) -> None:
    if not any("v" in s.pinyin_numeric for s in line.syllables):
        raise ValueError("Umlaut probe needs a Line with 女 or 绿 (v in pinyin_numeric)")
    audio = load_audio(path.read_bytes())
    for spelling in ("v", "u", "yu"):
        syllables = [s.model_copy(update={"pinyin_numeric": s.pinyin_numeric.replace("v", spelling)}) for s in line.syllables]
        spans = ctc.align(audio, syllables)
        print(f"umlaut={spelling}: {[None if s is None else s.model_dump() for s in spans]}")
        export_spans(audio, spans, folder, f"umlaut-{spelling}")
    print("Listen to all three sets of clips before selecting an umlaut spelling; default remains v.")


def evaluate(fixtures: Path, labels: dict, output: Path, report: Path | None = None) -> int:
    recordings = sorted((fixtures / "audio").glob("*.wav"))
    if not recordings:
        raise ValueError(f"No human WAV recordings in {fixtures / 'audio'}; checkpoint B is pending")
    if not isinstance(labels, dict):
        raise ValueError("--labels must map recording filenames to index lists")
    unknown = set(labels) - {path.name for path in recordings}
    if unknown:
        raise ValueError(f"Labels refer to unknown recordings: {sorted(unknown, key=str)}")
    prepared = []
    for path in recordings:
        name, variant, speaker = recording_name(path)
        line = Line.model_validate_json((fixtures / "lines" / f"{name}.json").read_text(encoding="utf-8"))
        errors = error_indices(line, variant, labels.get(path.name))
        validate_wav(path)
        prepared.append((path, line, errors, speaker, variant))
    totals = {"whisper": Counter(), "ctc": Counter()}
    by_speaker = {}
    records = []
    for path, line, errors, speaker, variant in prepared:
        audio = load_audio(path.read_bytes())
        transcript = transcribe(audio)
        # Production rejects no_speech before calling the optional CTC layer.
        if transcript.no_speech:
            base = finer = spans = [None] * len(line.syllables)
        else:
            observed = match(line.syllables, transcript.syllables)
            base = score_sounds_base(line.syllables, observed)
            spans = ctc.align(audio, line.syllables)
            finer = ctc.score_sounds(audio, line.syllables, spans)
        if not len(base) == len(finer) == len(spans) == len(line.syllables):
            raise ValueError(f"{path.name}: layer violated the per-syllable list rule")
        print(f"\n{path.name}: Whisper={transcript.text!r}, no_speech={transcript.no_speech}")
        speaker_totals = by_speaker.setdefault(speaker, {"whisper": Counter(), "ctc": Counter()})
        for index, syllable in enumerate(line.syllables):
            span = spans[index]
            timing = "missing" if span is None else f"{span.start_ms}-{span.end_ms}ms conf={span.confidence:.3f}"
            print(f"{index:2} {syllable.hanzi} {syllable.pinyin_numeric:7} "
                  f"whisper=[{_components(base[index])}] ctc=[{_components(finer[index])}] {timing}")
            for layer, result in (("whisper", base[index]), ("ctc", finer[index])):
                category = "errors" if index in errors else "correct"
                for count in (totals[layer], speaker_totals[layer]):
                    count[category] += 1
                    if flagged(result):
                        count["caught" if index in errors else "false_flags"] += 1
        export_spans(audio, spans, output, path.stem)
        records.append({
            "filename": path.name, "speaker": speaker, "variant": variant,
            "error_indices": sorted(errors), "transcript": transcript.text,
            "no_speech": transcript.no_speech, "trim_offset_ms": audio.trim_offset_ms,
            "syllables": [
                {"index": i, "pinyin_numeric": syllable.pinyin_numeric,
                 "deliberate_error": i in errors,
                 "span": None if spans[i] is None else spans[i].model_dump(),
                 **{layer: {"sound": None if scores[i] is None else scores[i].model_dump(),
                            "flagged": flagged(scores[i])}
                    for layer, scores in (("whisper", base), ("ctc", finer))}}
                for i, syllable in enumerate(line.syllables)
            ],
        })
    for layer, count in totals.items():
        print(f"{layer}: errors caught {count['caught']}/{count['errors']}; "
              f"correct syllables wrongly flagged {count['false_flags']}/{count['correct']}")
    for speaker, layers in sorted(by_speaker.items()):
        for layer, count in layers.items():
            print(f"speaker={speaker} {layer}: errors caught {count['caught']}/{count['errors']}; "
                  f"correct syllables wrongly flagged {count['false_flags']}/{count['correct']}")
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        # Explicit zeros keep reports comparable when a layer catches no errors.
        def counts(layers):
            return {layer: {key: count[key] for key in ("errors", "caught", "correct", "false_flags")}
                    for layer, count in layers.items()}
        payload = {"totals": counts(totals),
                   "speakers": {speaker: counts(layers) for speaker, layers in by_speaker.items()},
                   "recordings": records, "clips": str(output.resolve()),
                   "span_time_origin": "trimmed audio; add trim_offset_ms for original recording",
                   "checkpoint_decision": "pending team review"}
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Report: {report}")
    print(f"Clips: {output}\nTeam decision required: scores + boundaries / boundaries only / neither.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES)
    parser.add_argument("--labels", type=Path, help="JSON: recording filename -> deliberate-error indices")
    parser.add_argument("--output", type=Path, help="clip folder (default: persistent temporary folder)")
    parser.add_argument("--report", type=Path, help="save checkpoint counts and per-syllable evidence as JSON")
    parser.add_argument("--benchmark", type=Path, help="recording with at least five seconds")
    parser.add_argument("--umlaut", type=Path, help="recording of the supplied umlaut --line")
    parser.add_argument("--line", type=Path, help="Line JSON for benchmark/umlaut")
    parser.add_argument("--runs", type=int, default=3, help="warmed benchmark repetitions")
    args = parser.parse_args(argv)
    if args.runs < 1 or (args.benchmark or args.umlaut) and not args.line:
        parser.error("--runs must be positive; benchmark/umlaut require --line")
    if args.report and (args.benchmark or args.umlaut):
        parser.error("--report is for checkpoint evaluation, not benchmark/umlaut")
    try:
        output = args.output or Path(tempfile.mkdtemp(prefix="karaoke-ctc-"))
        if args.benchmark or args.umlaut:
            line = Line.model_validate_json(args.line.read_text(encoding="utf-8"))
            if args.benchmark:
                benchmark(args.benchmark, line, args.runs)
            if args.umlaut:
                umlaut_probe(args.umlaut, line, output)
            return 0
        labels = json.loads(args.labels.read_text(encoding="utf-8")) if args.labels else {}
        if not isinstance(labels, dict) or any(not isinstance(v, list) for v in labels.values()):
            raise ValueError("--labels must map recording filenames to index lists")
        return evaluate(args.fixtures, labels, output, args.report)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Evaluation failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
