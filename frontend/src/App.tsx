/**
 * The app: loads the song list and switches between the song screen and the line screen.
 *
 * Owner: A. Spec: docs/tasks/frontend.md.
 */
import { useEffect, useState } from "react";
import { ApiError, listSongs, type SongSummary } from "./api/client";

export default function App() {
  const [songs, setSongs] = useState<SongSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    listSongs(ctl.signal).then(setSongs, (e: ApiError) => e.code !== "cancelled" && setError(e.message));
    return () => ctl.abort();
  }, []);

  return (
    <main className="p-10">
      <h1 className="font-serif text-4xl">Karaoke Helper</h1>
      {error && <p className="mt-4 text-wrong">{error}</p>}
      <ul className="mt-6 space-y-2">
        {songs?.map((s) => (
          <li key={s.id} className="text-lg">
            <span className="font-serif">{s.title}</span> <span className="opacity-60">{s.artist}, {s.line_count} lines</span>
          </li>
        ))}
      </ul>
    </main>
  );
}
