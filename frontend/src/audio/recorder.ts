/**
 * Microphone capture.
 *
 * Records the user with MediaRecorder (webm/opus, browser audio processing turned
 * off), enforces the time limit, and exposes a live input level for the meter.
 *
 * The microphone is opened once, from the dock's prompt, and kept for the session.
 * "Use a simulated mic" records a hum made with Web Audio instead, for machines
 * without a microphone; it goes to the grader like any recording.
 *
 * Owner: A. Spec: docs/tasks/frontend.md ("Recording"), docs/design/ui.md §5.2.
 */

export type Mic = {
  stream: MediaStream;
  simulated: boolean;
  /** Input level from 0 to 1, read from an AnalyserNode on the same stream. */
  level(): number;
  close(): void;
};

export type Recording = {
  /** The recording, or null when it was cancelled. */
  done: Promise<Blob | null>;
  startedAt: number;
  limitMs: number;
  stop(): void;
  cancel(): void;
};

// Browser processing is designed for calls and can damage the consonants we grade.
const CONSTRAINTS: MediaStreamConstraints = {
  audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 },
};
const MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];

/** The microphone stays open for the session once allowed, so the prompt shows on the first Record only. */
export const sessionMic: { current: Mic | null } = { current: null };

let ctx: AudioContext | null = null;
function audioContext() {
  ctx ??= new AudioContext();
  void ctx.resume();
  return ctx;
}

function meter(source: AudioNode): () => number {
  const analyser = audioContext().createAnalyser();
  analyser.fftSize = 1024;
  source.connect(analyser);
  const buf = new Uint8Array(analyser.fftSize);
  return () => {
    analyser.getByteTimeDomainData(buf);
    let sum = 0;
    for (let i = 0; i < buf.length; i++) {
      const v = (buf[i] - 128) / 128;
      sum += v * v;
    }
    return Math.min(1, Math.sqrt(sum / buf.length) * 6);
  };
}

export async function openMic(): Promise<Mic> {
  const stream = await navigator.mediaDevices.getUserMedia(CONSTRAINTS);
  const source = audioContext().createMediaStreamSource(stream);
  return { stream, simulated: false, level: meter(source), close: () => stream.getTracks().forEach((t) => t.stop()) };
}

/** A sung-sounding hum, pulsing about three times a second like syllables. */
export function simulatedMic(): Mic {
  const c = audioContext();
  const voice = c.createOscillator();
  voice.type = "sawtooth";
  voice.frequency.value = 196;
  const tone = c.createBiquadFilter();
  tone.type = "lowpass";
  tone.frequency.value = 1400;
  const env = c.createGain();
  env.gain.value = 0.25;
  const pulse = c.createOscillator();
  pulse.frequency.value = 3;
  const depth = c.createGain();
  depth.gain.value = 0.25;
  pulse.connect(depth).connect(env.gain);
  voice.connect(tone).connect(env);
  const out = c.createMediaStreamDestination();
  env.connect(out);
  voice.start();
  pulse.start();
  return {
    stream: out.stream,
    simulated: true,
    level: meter(env),
    close: () => { voice.stop(); pulse.stop(); env.disconnect(); },
  };
}

export function startRecording(mic: Mic, limitMs: number): Recording {
  const mimeType = MIME_TYPES.find((m) => MediaRecorder.isTypeSupported(m));
  const rec = new MediaRecorder(mic.stream, mimeType ? { mimeType } : undefined);
  const chunks: Blob[] = [];
  let cancelled = false;
  rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
  const stop = () => { if (rec.state !== "inactive") rec.stop(); };
  const timer = setTimeout(stop, limitMs);
  const done = new Promise<Blob | null>((resolve) => {
    rec.onstop = () => {
      clearTimeout(timer);
      resolve(cancelled ? null : new Blob(chunks, { type: rec.mimeType || "audio/webm" }));
    };
  });
  rec.start();
  return {
    done,
    startedAt: performance.now(),
    limitMs,
    stop,
    cancel: () => { cancelled = true; stop(); },
  };
}
