/**
 * The app: loads the song list, owns the background and the song theme, and
 * switches between the song screen and the line screen. F toggles full screen
 * anywhere; nothing else changes the window.
 *
 * Starting a song opens no window: the song screen's title drifts away, the photo
 * blurs and darkens into the line screen's background, and the lyrics rise in.
 *
 * Owner: A. Spec: docs/tasks/frontend.md, docs/design/ui.md §3.3 ("Starting a song"), §4, §7 rule 4.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, getSong, listSongs, type Mode, type Song, type SongSummary } from "./api/client";
import { Backdrop, type BackdropHandle } from "./components/Backdrop";
import { Toaster } from "./components/Toast";
import { betweenAmount, crossfadeWeights } from "./logic/recordWheel";
import { buildEntries } from "./logic/songList";
import LineScreen from "./screens/LineScreen";
import SongScreen from "./screens/SongScreen";
import { applyPalette, SONG_THEMES } from "./theme/songThemes";

const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export default function App() {
  const [songs, setSongs] = useState<SongSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState(0);
  const [song, setSong] = useState<Song | null>(null);
  const [mode, setMode] = useState<Mode>("spoken");
  const [leaving, setLeaving] = useState(false);
  const [arriving, setArriving] = useState(false);
  const backdrop = useRef<BackdropHandle>(null);

  // Nothing shows until the list arrives, so a themed "coming soon" song never flashes first.
  // If the backend can't be reached, the themed songs still show, all coming soon.
  const entries = useMemo(() => (songs || error ? buildEntries(songs ?? [], SONG_THEMES) : []), [songs, error]);
  const entry = entries[selected];

  const load = useCallback((signal?: AbortSignal) => {
    setError(null);
    listSongs(signal).then(setSongs, (e: ApiError) => e.code !== "cancelled" && setError(e.message));
  }, []);

  useEffect(() => {
    const ctl = new AbortController();
    load(ctl.signal);
    return () => ctl.abort();
  }, [load]);

  useEffect(() => {
    if (entry) applyPalette(entry.theme.palette);
  }, [entry]);

  // F toggles the browser's full screen anywhere in the app.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() !== "f" || e.metaKey || e.ctrlKey || e.altKey) return;
      if ((e.target as HTMLElement).matches?.("input, textarea")) return;
      e.preventDefault();
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
      else document.documentElement.requestFullscreen?.().catch(() => {});
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  // The record's position drives the photos' crossfade and the grain, every frame, without re-rendering.
  const onTurn = useCallback((u: number) => {
    backdrop.current?.setWeights(crossfadeWeights(u, entries.length));
    document.documentElement.style.setProperty("--grain", (0.1 + 0.34 * betweenAmount(u)).toFixed(3));
  }, [entries.length]);

  const start = (m: Mode) => {
    if (!entry?.playable || leaving) return;
    setLeaving(true);
    backdrop.current?.setWeights(entries.map((_, k) => (k === selected ? 1 : 0)));
    const drift = new Promise((r) => setTimeout(r, reduced() ? 0 : 560));
    Promise.all([getSong(entry.id), drift]).then(
      ([s]) => { setMode(m); setSong(s); setLeaving(false); },
      (e: ApiError) => { setLeaving(false); setError(e.message); },
    );
  };

  const exit = () => {
    setSong(null);
    setArriving(true);
    setTimeout(() => setArriving(false), 1000);
  };

  return (
    <div className={`app${song || leaving ? " singing" : ""}`} style={{ height: "100%" }}>
      <Backdrop ref={backdrop} entries={entries} selected={selected} />
      <div className="scrim" />
      <div className="grain" aria-hidden />
      <div className="stage">
        {song
          ? <LineScreen key={song.id} song={song} mode={mode} onExit={exit} />
          : <SongScreen entries={entries} selected={selected} onSelect={setSelected} onTurn={onTurn} onStart={start}
              leaving={leaving} arriving={arriving} error={error} onRetry={() => load()} />}
      </div>
      <Toaster />
      <div className="narrow">Karaoke Helper is built for laptops and desktops.<br />Open it on a wider screen to sing along.</div>
    </div>
  );
}
