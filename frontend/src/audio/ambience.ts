/**
 * Ambience: a faint vinyl crackle on the song screen, and radio static that rises
 * while the record is between two songs. Generated with Web Audio; no files.
 * Browsers allow sound only after a click or a key press, so it starts on the first.
 *
 * Opening a page's first AudioContext takes about 0.2 s while the audio device
 * starts (unless a track is already playing). Built on the first click, that froze
 * whatever the click began, opening Sing say, so it is built as the page loads,
 * suspended, and the first click or key press only resumes it.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("Between songs"), §6 (Ambience).
 */

/** Loudness of the crackle while the record plays, and of the static halfway between two songs (0–1). */
const CRACKLE_LEVEL = 0.05;
const STATIC_LEVEL = 0.05;

let ctx: AudioContext | null = null;
let crackle: GainNode | null = null;
let noise: GainNode | null = null;
let active = false;
let playing = false;
let level = 0;

function loop(c: AudioContext, seconds: number, fill: (d: Float32Array) => void) {
  const buf = c.createBuffer(1, c.sampleRate * seconds, c.sampleRate);
  fill(buf.getChannelData(0));
  const src = c.createBufferSource();
  src.buffer = buf;
  src.loop = true;
  src.start();
  return src;
}

function build() {
  if (ctx) return;
  try {
    const c = (ctx = new AudioContext());
    crackle = c.createGain();
    crackle.gain.value = 0;
    const lp = c.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.value = 5000;
    loop(c, 3, (d) => {
      for (let i = 0; i < d.length; i++) {
        d[i] += (Math.random() * 2 - 1) * 0.004;
        if (Math.random() < 0.0004) {
          const a = (Math.random() * 0.2 + 0.05) * (Math.random() < 0.5 ? -1 : 1);
          for (let j = 0; j < 40 && i + j < d.length; j++) d[i + j] += a * Math.exp(-j / 6);
        }
      }
    }).connect(lp).connect(crackle).connect(c.destination);

    noise = c.createGain();
    noise.gain.value = 0;
    const bp = c.createBiquadFilter();
    bp.type = "bandpass";
    bp.frequency.value = 2400;
    bp.Q.value = 0.6;
    loop(c, 2, (d) => { for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1; }).connect(bp).connect(noise).connect(c.destination);
    apply();
  } catch {
    ctx = null;
  }
}

function apply() {
  if (!ctx || !crackle || !noise) return;
  const t = ctx.currentTime;
  crackle.gain.setTargetAtTime(active && playing ? CRACKLE_LEVEL : 0, t, 0.2);
  noise.gain.setTargetAtTime(active ? level * STATIC_LEVEL : 0, t, 0.03);
}

function start() {
  build();
  ctx?.resume().catch(() => {});
}

if (typeof document !== "undefined") {
  build();
  for (const ev of ["pointerdown", "keydown"]) document.addEventListener(ev, start, { once: true });
}

/** On while the song screen shows and sound is on; the crackle only while the record plays. */
export function setAmbienceActive(on: boolean, recordPlaying: boolean) {
  active = on;
  playing = recordPlaying;
  apply();
}

/** 0 on a song, 1 halfway between two. */
export function setStatic(between: number) {
  level = between;
  apply();
}
