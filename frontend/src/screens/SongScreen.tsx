/**
 * Song screen: the song list and the mode choice.
 *
 * The user picks a song and, when VITE_SHOW_MODE_CHOICE is on, spoken or singing
 * accuracy, then starts at line 1.
 *
 * The design (ui.md §5.1): each song's photograph is the page, its title is set
 * huge in a hairline serif, and the songs ride a huge record on the right. Turning
 * the record changes songs; once it settles, a short preview plays.
 *
 * Owner: A. Spec: docs/tasks/frontend.md, docs/design/ui.md §4.1, §5.1.
 */
import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import { getSong, type Mode, type Song } from "../api/client";
import { setAmbienceActive, setStatic } from "../audio/ambience";
import { playPreview, type Playback } from "../audio/player";
import { Credit } from "../components/song/Credit";
import { HomeHeader } from "../components/song/HomeHeader";
import { LyricSample } from "../components/song/LyricSample";
import { MODE_HINT, SingButton } from "../components/song/SingButton";
import { SongRecord, type SongRecordHandle } from "../components/song/SongRecord";
import { SongTitle } from "../components/song/SongTitle";
import { SHOW_MODE_CHOICE } from "../config";
import { useLatest } from "../hooks/useLatest";
import { useWindowSize } from "../hooks/useWindowSize";
import { betweenAmount, wheelGeometry } from "../logic/recordWheel";
import type { Entry } from "../logic/songList";

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

let soundOn = true;
const songs = new Map<string, Promise<Song>>();
const songFor = (id: string) => {
  if (!songs.has(id)) songs.set(id, getSong(id).catch((e) => { songs.delete(id); throw e; }));
  return songs.get(id)!;
};

export default function SongScreen({ entries, selected, onSelect, onTurn, onStart, leaving, arriving, error, onRetry }: Props) {
  const { w: W, h: H } = useWindowSize();
  const root = useRef<HTMLElement>(null);
  const record = useRef<SongRecordHandle>(null);
  const preview = useRef<Playback | null>(null);
  const previewTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const [picking, setPicking] = useState(false);
  const [hint, setHint] = useState<Mode | "none">("none");
  const [sound, setSound] = useState(soundOn);
  const [previewing, setPreviewing] = useState(false);

  const entry = entries[selected];
  const g = wheelGeometry(W, H, W * 0.48, 0);
  const avail = g.discLeft - W * 0.07 - 72; // every title line ends at least 72px before the record
  const indent = Math.round(Math.min(W * 0.12, 180, avail * 0.3));
  const copyw = Math.max(260, Math.min(460, avail - indent));

  // ---- preview ----
  const stopPreview = useCallback(() => {
    clearTimeout(previewTimer.current);
    preview.current?.stop();
    preview.current = null;
    setPreviewing(false);
  }, []);
  const live = useLatest({ entries, sound, leaving });
  const onSettle = useCallback((k: number) => {
    stopPreview();
    previewTimer.current = setTimeout(() => {
      const { entries, sound, leaving } = live.current;
      const e = entries[k];
      if (!sound || leaving || !e?.playable) return;
      songFor(e.id).then((song) => {
        if (live.current.entries[k]?.id !== e.id || !live.current.sound || preview.current) return;
        const pb = playPreview(song.audio_url, song.lines[0]?.start_ms ?? 0, () => setPreviewing(true));
        preview.current = pb;
        pb.done.then(() => { if (preview.current === pb) { preview.current = null; setPreviewing(false); } });
      }, () => {});
    }, 450);
  }, [live, stopPreview]);

  useEffect(() => stopPreview, [stopPreview]);
  useEffect(() => { if (leaving || !sound) stopPreview(); }, [leaving, sound, stopPreview]);

  // ---- ambience ----
  useEffect(() => {
    setAmbienceActive(sound && !leaving);
    return () => setAmbienceActive(false);
  }, [sound, leaving]);

  const turn = useCallback((u: number) => {
    onTurn(u);
    setStatic(betweenAmount(u));
  }, [onTurn]);

  const gestureStart = useCallback(() => { stopPreview(); setPicking(false); }, [stopPreview]);

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
    if (leaving) return;
    if (e.key === "Escape") return setPicking(false);
    if (picking && e.key.startsWith("Arrow")) return;
    if (e.key === "ArrowDown" || e.key === "ArrowRight") { e.preventDefault(); record.current?.step(1); }
    else if (e.key === "ArrowUp" || e.key === "ArrowLeft") { e.preventDefault(); record.current?.step(-1); }
    else if (e.key === "Enter" && !(e.target as HTMLElement).closest?.("button")) {
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

  const toggleSound = () => {
    soundOn = !sound;
    setSound(soundOn);
  };

  const t = entry?.theme;
  return (
    <section ref={root} className={`home${leaving ? " leaving" : ""}${arriving ? " arriving" : ""}`}>
      <div className="h-shade" />
      <HomeHeader sound={sound} onSound={toggleSound} />

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
          key={entries.map((e) => `${e.id}:${+e.playable}`).join("|")}
          ref={record}
          entries={entries}
          g={g}
          initial={selected}
          previewing={previewing}
          onTurn={turn}
          onSelect={onSelect}
          onSettle={onSettle}
          onGestureStart={gestureStart}
        />
      )}

      {t && <LyricSample sample={t.sample} />}
      {t && <Credit theme={t} />}
      {error && (
        <div className="home-error note" role="alert">
          {error} <button className="btn" style={{ height: 34, marginLeft: 10 }} onClick={onRetry}>Try again</button>
        </div>
      )}
    </section>
  );
}
