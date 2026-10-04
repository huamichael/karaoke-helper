/**
 * Song screen: the song list and the mode choice.
 *
 * The user picks a song and, when VITE_SHOW_MODE_CHOICE is on, spoken or singing
 * accuracy, then starts at line 1.
 *
 * The design (ui.md §5.1): each song's photograph is the page, its title is set
 * huge in a hairline serif, and the songs ride a huge record on the right, pasted
 * onto the photo like a collage. The record is a turntable: arm on the record =
 * playing (the platter turns and a short preview plays); arm on its rest =
 * stopped. The cover, the arm or Space plays and stops it; the cap on the arm's
 * pivot (or M) turns the sound on and off.
 *
 * Owner: A. Spec: docs/tasks/frontend.md, docs/design/ui.md §4.1, §5.1.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { getSong, type Mode, type Song } from "../api/client";
import { setAmbienceActive, setStatic } from "../audio/ambience";
import { playRecord, type RecordPlayback } from "../audio/player";
import { CoverButton } from "../components/song/CoverButton";
import { Credit } from "../components/song/Credit";
import { HomeHeader } from "../components/song/HomeHeader";
import { LyricSubtitle } from "../components/song/LyricSubtitle";
import { Scraps } from "../components/song/Scraps";
import { MODE_HINT, SingButton } from "../components/song/SingButton";
import { SongRecord, type SongRecordHandle } from "../components/song/SongRecord";
import { SongTitle } from "../components/song/SongTitle";
import { SoundCap } from "../components/song/SoundCap";
import { Tonearm, type ArmPlace, type TonearmHandle } from "../components/song/Tonearm";
import { SHOW_MODE_CHOICE } from "../config";
import { useLatest } from "../hooks/useLatest";
import { useWindowSize } from "../hooks/useWindowSize";
import { betweenAmount, wheelGeometry } from "../logic/recordWheel";
import { previewWindow } from "../logic/subtitle";
import type { Entry } from "../logic/songList";
import { armLayout } from "../logic/turntable";

type Props = {
  entries: Entry[];
  selected: number;
  onSelect(i: number): void;
  /** Every frame the record turns: the backdrop and the grain follow it. */
  onTurn(u: number): void;
  onStart(mode: Mode): void;
  leaving: boolean;
  arriving: boolean;
  error: string | null;
  onRetry(): void;
};

// The sound switch and the turntable keep their state across visits to the song screen.
let soundOn = true;
let recordOn = true;
const songs = new Map<string, Promise<Song>>();
const songFor = (id: string) => {
  if (!songs.has(id)) songs.set(id, getSong(id).catch((e) => { songs.delete(id); throw e; }));
  return songs.get(id)!;
};

export default function SongScreen({ entries, selected, onSelect, onTurn, onStart, leaving, arriving, error, onRetry }: Props) {
  const { w: W, h: H } = useWindowSize();
  const root = useRef<HTMLElement>(null);
  const record = useRef<SongRecordHandle>(null);
  const arm = useRef<TonearmHandle>(null);
  const audio = useRef<RecordPlayback | null>(null);
  const settleTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const playingNow = useRef(recordOn); // read by async arm callbacks before React re-renders
  const [picking, setPicking] = useState(false);
  const [hint, setHint] = useState<Mode | "none">("none");
  const [sound, setSound] = useState(soundOn);
  const [playing, setPlaying] = useState(recordOn);
  const [spinning, setSpinning] = useState(recordOn);
  const [previewing, setPreviewing] = useState(false);

  const entry = entries[selected];
  const g = useMemo(() => wheelGeometry(W, H, W * 0.48, 0), [W, H]);
  const dialW = W * 0.52;
  const pivot = armLayout(g, dialW, H).pivot;
  const avail = g.discLeft - W * 0.07 - 72; // every title line ends at least 72px before the record
  const indent = Math.round(Math.min(W * 0.12, 180, avail * 0.3));
  const copyw = Math.max(260, Math.min(460, avail - indent));
  const live = useLatest({ entries, selected, sound, leaving, previewing });
  const go = (where: ArmPlace) => arm.current?.go(where) ?? Promise.resolve(true);

  // ---- the preview: plays while the arm is down on a playable song (muted while sound is off) ----
  const stopAudio = useCallback(() => { audio.current?.stop(); audio.current = null; }, []);
  const startAudio = useCallback((k: number) => {
    const e = live.current.entries[k];
    if (!e?.playable || audio.current) return;
    songFor(e.id).then((song) => {
      const now = live.current;
      if (!playingNow.current || now.leaving || now.entries[now.selected]?.id !== e.id || audio.current || !song.lines.length) return;
      const pb = playRecord(song.audio_url, previewWindow(song.lines), !now.sound);
      audio.current = pb;
      pb.done.then(() => { if (audio.current === pb) audio.current = null; });
    }, () => {});
  }, [live]);
  const trackTime = useCallback(() => audio.current?.timeMs() ?? null, []);

  // The subtitle shows the lyric of the song on the record.
  const [lyrics, setLyrics] = useState<Song | null>(null);
  useEffect(() => {
    if (!entry?.playable) return setLyrics(null);
    let alive = true;
    songFor(entry.id).then((s) => { if (alive) setLyrics(s); }, () => { if (alive) setLyrics(null); });
    return () => { alive = false; };
  }, [entry?.id, entry?.playable]);
  const stopPreview = useCallback(() => {
    clearTimeout(settleTimer.current);
    stopAudio();
    setPreviewing(false);
  }, [stopAudio]);
  const startPreview = useCallback((k: number) => {
    const { entries, leaving } = live.current;
    if (!playingNow.current || leaving || !entries[k]?.playable) return;
    setPreviewing(true);
    startAudio(k);
  }, [live, startAudio]);

  // ---- the turntable ----
  const setRecord = (on: boolean) => {
    recordOn = on;
    playingNow.current = on;
    setPlaying(on);
    clearTimeout(settleTimer.current);
    if (on) {
      setSpinning(true);
      go("play").then((ok) => { if (ok) startPreview(live.current.selected); });
    } else {
      stopPreview();
      go("rest").then((ok) => { if (ok && !playingNow.current) setSpinning(false); });
    }
  };
  const toggleRecord = () => { if (!live.current.leaving) setRecord(!playingNow.current); };
  const toggleSound = () => {
    soundOn = !live.current.sound;
    setSound(soundOn);
    audio.current?.setMuted(!soundOn);
  };

  // Changing songs while it plays lifts the arm on the cue lever; it sets down again once the record settles.
  const gestureStart = useCallback(() => {
    stopPreview();
    setPicking(false);
    if (playingNow.current) arm.current?.go("cue");
  }, [stopPreview]);
  const onSettle = useCallback((k: number) => {
    clearTimeout(settleTimer.current);
    if (!playingNow.current) return;
    settleTimer.current = setTimeout(() => {
      (arm.current?.go("play") ?? Promise.resolve(true)).then((ok) => { if (ok) startPreview(k); });
    }, 220);
  }, [startPreview]);

  // On load the record starts like a real one: the arm moves from its rest onto the record.
  const recordKey = entries.map((e) => `${e.id}:${+e.playable}`).join("|");
  useEffect(() => {
    if (!recordKey || !playingNow.current) return;
    setSpinning(true);
    (arm.current?.go("play") ?? Promise.resolve(true)).then((ok) => { if (ok) startPreview(live.current.selected); });
    return stopPreview;
  }, [recordKey, live, startPreview, stopPreview]);

  useEffect(() => {
    if (!leaving) return;
    stopPreview();
    setSpinning(false);
  }, [leaving, stopPreview]);

  // ---- ambience ----
  useEffect(() => {
    setAmbienceActive(sound && !leaving, playing);
    return () => setAmbienceActive(false, false);
  }, [sound, leaving, playing]);

  const turn = useCallback((u: number) => {
    onTurn(u);
    setStatic(betweenAmount(u));
  }, [onTurn]);

  // ---- input: wheel anywhere on the screen, keys ----
  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const f = (e: WheelEvent) => record.current?.wheel(e);
    el.addEventListener("wheel", f, { passive: false });
    return () => el.removeEventListener("wheel", f);
  }, []);

  const start = (mode: Mode) => {
    if (!entry?.playable || leaving) return;
    stopPreview();
    setPicking(false);
    onStart(mode);
  };
  const keys = useLatest((e: KeyboardEvent) => {
    if (leaving || e.metaKey || e.ctrlKey || e.altKey) return;
    const onButton = !!(e.target as HTMLElement).closest?.("button, input, textarea");
    if (e.key === "Escape") return setPicking(false);
    if (e.key === " " && !onButton) { e.preventDefault(); return toggleRecord(); }
    if (e.key === "m" || e.key === "M") return toggleSound();
    if (picking && e.key.startsWith("Arrow")) return;
    if (e.key === "ArrowDown" || e.key === "ArrowRight") { e.preventDefault(); record.current?.step(1); }
    else if (e.key === "ArrowUp" || e.key === "ArrowLeft") { e.preventDefault(); record.current?.step(-1); }
    else if (e.key === "Enter" && !onButton) {
      e.preventDefault();
      if (!entry?.playable) return;
      if (SHOW_MODE_CHOICE) { setHint("none"); setPicking(true); } else start("spoken");
    }
  });
  useEffect(() => {
    const f = (e: KeyboardEvent) => keys.current(e);
    document.addEventListener("keydown", f);
    return () => document.removeEventListener("keydown", f);
  }, [keys]);

  const t = entry?.theme;
  return (
    <section ref={root} className={`home${leaving ? " leaving" : ""}${arriving ? " arriving" : ""}`}>
      <div className="h-shade" />
      <HomeHeader />

      {entry && (
        <div className="h-main" style={{ "--indent": `${indent}px`, "--copyw": `${copyw}px` } as CSSProperties}>
          <SongTitle entry={entry} avail={avail} height={H} />
          <div className={`h-copy${picking ? " picking" : ""}`} key={entry.id}>
            {(t?.titlePinyin || t?.titleEnglish) && (
              <p className="h-sub">{t.titlePinyin && <span>{t.titlePinyin}</span>}{t.titleEnglish && <span>{t.titleEnglish}</span>}</p>
            )}
            {t?.blurb && <p className="h-blurb">{t.blurb}</p>}
            <div className="h-cta">
              {entry.playable
                ? <SingButton title={entry.title} showChoice={SHOW_MODE_CHOICE} picking={picking} onPicking={setPicking} onHint={setHint} onStart={start} />
                : <><button className="btn" disabled>Coming soon</button><span className="h-meta">This song isn't on the server yet</span></>}
            </div>
            <p className="sing-hint" aria-live="polite">{picking ? MODE_HINT[hint] : ""}</p>
          </div>
        </div>
      )}

      {entries.length > 0 && (
        <SongRecord
          key={recordKey}
          ref={record}
          entries={entries}
          g={g}
          initial={selected}
          spinning={spinning}
          previewing={previewing}
          onTurn={turn}
          onSelect={onSelect}
          onSettle={onSettle}
          onGestureStart={gestureStart}
          between={entry && <Scraps songId={entry.id} theme={entry.theme} g={g} W={W} H={H} />}
        >
          <CoverButton cx={g.cx} cy={g.cy} rl={g.rl} playing={playing} onToggle={toggleRecord} />
          <Tonearm ref={arm} g={g} width={dialW} height={H} accent={t?.palette.accent ?? "#ece8ff"} host={root} onToggle={toggleRecord} />
          <SoundCap x={pivot.x} y={pivot.y} sound={sound} onToggle={toggleSound} />
        </SongRecord>
      )}

      {entry && lyrics?.id === entry.id && <LyricSubtitle songId={entry.id} lines={lyrics.lines} timeMs={trackTime} />}
      {t && <Credit theme={t} />}
      {error && (
        <div className="home-error note" role="alert">
          {error} <button className="btn" style={{ height: 34, marginLeft: 10 }} onClick={onRetry}>Try again</button>
        </div>
      )}
    </section>
  );
}
