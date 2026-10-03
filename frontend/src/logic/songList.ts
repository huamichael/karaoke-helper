/**
 * The songs on the record: the backend's songs, in its order, then any themed
 * song the backend does not serve yet, shown as "Coming soon".
 *
 * The title comes from the backend; the artist shown is the theme's (the artist
 * of the recording we sing along to) when it has one.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("A song that isn't ready still tunes in").
 */
import type { SongSummary } from "../api/client";
import { FALLBACK_PALETTE, type SongTheme } from "../theme/songThemes";

export type Entry = { id: string; title: string; artist: string; playable: boolean; theme: SongTheme };

export function buildEntries(songs: SongSummary[], themes: Record<string, SongTheme>): Entry[] {
  const served = songs.map((s) => {
    const theme = themes[s.id] ?? { palette: FALLBACK_PALETTE };
    return { id: s.id, title: s.title, artist: theme.artist ?? s.artist, playable: true, theme };
  });
  const ids = new Set(songs.map((s) => s.id));
  const soon = Object.entries(themes)
    .filter(([id, t]) => !ids.has(id) && t.title)
    .map(([id, t]) => ({ id, title: t.title!, artist: t.artist ?? "", playable: false, theme: t }));
  return [...served, ...soon];
}
