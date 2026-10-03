/**
 * The app: loads the song list, owns the background and the song theme, and
 * switches between the song screen and the line screen. F toggles full screen
 * anywhere; nothing else changes the window.
 *
 * Owner: A. Spec: docs/tasks/frontend.md, docs/design/ui.md §4, §7 rule 4.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError, getSong, listSongs, type Mode, type Song, type SongSummary } from "./api/client";
import { Backdrop, type BackdropHandle } from "./components/Backdrop";
import { Toaster } from "./components/Toast";
import { buildEntries } from "./logic/songList";
import LineScreen from "./screens/LineScreen";
import SongScreen from "./screens/SongScreen";
import { applyPalette, SONG_THEMES } from "./theme/songThemes";

export default function App() {
  const [songs, setSongs] = useState<SongSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState(0);
  const [song, setSong] = useState<Song | null>(null);
  const [mode, setMode] = useState<Mode>("spoken");
  const backdrop = useRef<BackdropHandle>(null);

  const entries = useMemo(() => buildEntries(songs, SONG_THEMES), [songs]);
  const entry = entries[selected];

  useEffect(() => {
    const ctl = new AbortController();
    listSongs(ctl.signal).then(setSongs, (e: ApiError) => e.code !== "cancelled" && setError(e.message));
    return () => ctl.abort();
  }, []);

  useEffect(() => {
    if (entry) applyPalette(entry.theme.palette);
  }, [entry]);

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

  const start = (m: Mode) => {
    if (!entry?.playable) return;
    getSong(entry.id).then(
      (s) => { setMode(m); setSong(s); },
      (e: ApiError) => setError(e.message),
    );
  };

  return (
    <div className={`app${song ? " singing" : ""}`} style={{ height: "100%" }}>
      <Backdrop ref={backdrop} entries={entries} selected={selected} />
      <div className="scrim" />
      <div className="grain" aria-hidden />
      <div className="stage">
        {song
          ? <LineScreen key={song.id} song={song} mode={mode} onExit={() => setSong(null)} />
          : <SongScreen entries={entries} selected={selected} onSelect={setSelected} onStart={start} error={error} />}
      </div>
      <Toaster />
      <div className="narrow">Karaoke Helper is built for laptops and desktops.<br />Open it on a wider screen to sing along.</div>
    </div>
  );
}
