/**
 * Playback.
 *
 * Plays one line of the track between its start and end times, and plays a word's
 * spoken reference clip, falling back to browser speech synthesis when there is no
 * clip.
 *
 * One <audio> element serves the track. Its position is polled every frame,
 * because `timeupdate` fires too rarely to stop on time. When the track cannot
 * play (a song bundle without its audio file yet), the line is spoken instead and
 * the karaoke fill runs over the line's own duration.
 *
 * Owner: A. Spec: docs/tasks/frontend.md ("Playing a line", "Spoken reference in Word practice").
 */
import { mediaUrl, type Line, type Word } from "../api/client";
import { loopTime } from "../logic/subtitle";
import { pickVoice } from "../logic/voice";

export type Playback = { done: Promise<"ended" | "stopped">; stop(): void };

let track: HTMLAudioElement | null = null;
const trackEl = () => (track ??= Object.assign(new Audio(), { preload: "auto" }));

/** Load the track early so the first Listen starts at once. */
export function preloadTrack(audioUrl: string) {
  const el = trackEl(), src = mediaUrl(audioUrl);
  if (el.src !== src) el.src = src;
}

function controlled(start: (finish: (r: "ended" | "stopped") => void) => () => void): Playback {
  let resolve!: (r: "ended" | "stopped") => void;
  let settled = false;
  let cleanup: (() => void) | null = null;
  const done = new Promise<"ended" | "stopped">((r) => (resolve = r));
  const finish = (r: "ended" | "stopped") => {
    if (settled) return;
    settled = true;
    cleanup?.();
    resolve(r);
  };
  cleanup = start(finish);
  if (settled) cleanup();
  return { done, stop: () => finish("stopped") };
}

/** Plays [start_ms, end_ms] of the track. onTick gets the track position in ms every frame. */
export function playLine(audioUrl: string, line: Pick<Line, "start_ms" | "end_ms" | "text">, onTick: (ms: number) => void): Playback {
  return controlled((finish) => {
    const el = trackEl();
    preloadTrack(audioUrl);
    let raf = 0, fallback: Playback | null = null, live = true;
    const tick = () => {
      const ms = el.currentTime * 1000;
      if (ms >= line.end_ms) {
        onTick(line.end_ms);
        finish("ended");
        return;
      }
      onTick(ms);
      raf = requestAnimationFrame(tick);
    };
    el.currentTime = line.start_ms / 1000;
    el.play().then(
      () => { if (live) raf = requestAnimationFrame(tick); else el.pause(); },
      () => {
        if (!live) return;
        fallback = speakLine(line, onTick);
        fallback.done.then(finish);
      },
    );
    return () => {
      live = false;
      cancelAnimationFrame(raf);
      el.pause();
      fallback?.stop();
    };
  });
}

/** Without a track: speak the line and run the fill over the line's duration. */
function speakLine(line: Pick<Line, "start_ms" | "end_ms" | "text">, onTick: (ms: number) => void): Playback {
  return controlled((finish) => {
    const t0 = performance.now();
    const speech = speak(line.text, 0.8);
    let raf = requestAnimationFrame(function tick(now) {
      const ms = line.start_ms + (now - t0);
      onTick(Math.min(ms, line.end_ms));
      if (ms >= line.end_ms) finish("ended");
      else raf = requestAnimationFrame(tick);
    });
    return () => { cancelAnimationFrame(raf); speech.stop(); };
  });
}

export type RecordPlayback = Playback & {
  /** The track position in ms while it plays (heard or muted), else null. */
  timeMs(): number | null;
  setMuted(muted: boolean): void;
};

const RECORD_VOLUME = 0.8;
const FADE_MS = 800;
const STOP_FADE_MS = 250;

/**
 * The song screen's record: plays [fromMs, toMs] of the track on a loop for as
 * long as the arm is down, fading in at the start of each pass and out before the
 * loop. Muted, it keeps playing silently, so the lyric subtitle stays in time.
 * Browsers refuse sound before the first click or key press; then it plays muted
 * and unmutes on the first one. Stopping fades out over a quarter second. With
 * no track to play, the lyric still goes round on a silent clock.
 */
export function playRecord(audioUrl: string, win: { fromMs: number; toMs: number }, muted: boolean): RecordPlayback {
  const a = new Audio(mediaUrl(audioUrl));
  a.preload = "auto";
  a.volume = 0;
  a.muted = muted;
  a.currentTime = win.fromMs / 1000;
  let want = muted, blocked = false, raf = 0, stoppingAt = 0, silentSince = 0, settled = false;
  let resolve!: (r: "ended" | "stopped") => void;
  const done = new Promise<"ended" | "stopped">((r) => (resolve = r));
  const unlock = () => { blocked = false; a.muted = want; };
  const finish = (r: "ended" | "stopped") => {
    if (settled) return;
    settled = true;
    cancelAnimationFrame(raf);
    a.pause();
    a.removeAttribute("src");
    document.removeEventListener("pointerdown", unlock);
    document.removeEventListener("keydown", unlock);
    resolve(r);
  };
  const frame = (now: number) => {
    let ms = a.currentTime * 1000;
    if (ms >= win.toMs) {
      a.currentTime = win.fromMs / 1000;
      ms = win.fromMs;
    }
    let v = Math.max(0, Math.min(1, (ms - win.fromMs) / FADE_MS, (win.toMs - ms) / FADE_MS));
    if (stoppingAt) {
      const k = (now - stoppingAt) / STOP_FADE_MS;
      if (k >= 1) return finish("stopped");
      v *= 1 - k;
    }
    a.volume = v * RECORD_VOLUME;
    raf = requestAnimationFrame(frame);
  };
  const start = () => { if (!settled) raf = requestAnimationFrame(frame); };
  // If the file itself ends before the window does, go round again all the same.
  a.onended = () => {
    if (settled || stoppingAt || silentSince) return;
    a.currentTime = win.fromMs / 1000;
    a.play().catch(() => {});
  };
  // No track to play (none in the bundle yet, or it cannot be decoded): keep time silently, still looping,
  // so the lyric on the song screen goes on going round.
  const silent = () => {
    if (settled) return;
    silentSince = performance.now();
    a.removeAttribute("src");
  };
  a.play().then(start, (e: DOMException) => {
    if (settled) return;
    if (e.name !== "NotAllowedError" || a.muted) return silent();
    blocked = true;
    a.muted = true;
    document.addEventListener("pointerdown", unlock, { once: true });
    document.addEventListener("keydown", unlock, { once: true });
    a.play().then(start, silent);
  });
  return {
    done,
    stop: () => {
      if (settled) return;
      if (silentSince || a.paused || stoppingAt) return finish("stopped");
      stoppingAt = performance.now();
    },
    timeMs: () => {
      if (settled) return null;
      if (silentSince) return loopTime(win, performance.now() - silentSince);
      return !a.paused && a.readyState >= 2 ? a.currentTime * 1000 : null;
    },
    setMuted: (m) => {
      want = m;
      if (!blocked) a.muted = m;
    },
  };
}

/** The spoken reference: the word's clip, or speechSynthesis in zh-CN when audio_url is null. */
export function playWord(word: Pick<Word, "text" | "audio_url">): Playback {
  if (!word.audio_url) return speak(word.text, 0.8);
  return controlled((finish) => {
    const a = new Audio(mediaUrl(word.audio_url!));
    let fallback: Playback | null = null;
    a.onended = () => finish("ended");
    a.play().catch(() => { fallback = speak(word.text, 0.8); fallback.done.then(finish); });
    return () => { a.pause(); fallback?.stop(); };
  });
}

// The Mandarin voice for browser speech (logic/voice.ts). Chrome loads its voice list late, so it is
// looked up on first use once the list exists, and again whenever the list changes.
let chosenVoice: SpeechSynthesisVoice | null | undefined;
function mandarinVoice(): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis?.getVoices() ?? [];
  if (!voices.length) return null;
  if (chosenVoice === undefined) chosenVoice = pickVoice(voices);
  return chosenVoice;
}
if (typeof window !== "undefined" && window.speechSynthesis) {
  window.speechSynthesis.getVoices(); // starts Chrome loading the list
  window.speechSynthesis.addEventListener?.("voiceschanged", () => { chosenVoice = undefined; });
}

/** Browser speech. Resolves when done, or after a generous guess if the voice never reports back. */
export function speak(text: string, rate = 0.8): Playback {
  return controlled((finish) => {
    const guess = setTimeout(() => finish("ended"), [...text].length * 650 + 800);
    const synth = window.speechSynthesis;
    if (synth) {
      synth.cancel();
      const u = new SpeechSynthesisUtterance(text);
      const voice = mandarinVoice();
      u.lang = voice?.lang ?? "zh-CN";
      if (voice) u.voice = voice;
      u.rate = rate;
      u.onend = () => finish("ended");
      synth.speak(u);
    }
    return () => { clearTimeout(guess); synth?.cancel(); };
  });
}
