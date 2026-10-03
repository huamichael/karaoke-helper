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

/** Browser speech. Resolves when done, or after a generous guess if the voice never reports back. */
export function speak(text: string, rate = 0.8): Playback {
  return controlled((finish) => {
    const guess = setTimeout(() => finish("ended"), [...text].length * 650 + 800);
    const synth = window.speechSynthesis;
    if (synth) {
      synth.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "zh-CN";
      u.rate = rate;
      u.onend = () => finish("ended");
      synth.speak(u);
    }
    return () => { clearTimeout(guess); synth?.cancel(); };
  });
}
