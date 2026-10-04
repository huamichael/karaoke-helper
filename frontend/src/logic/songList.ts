/**
 * The songs on the record: the backend's songs, in its order, then any themed
 * song the backend does not serve yet, shown as "Coming soon".
 *
 * The theme's title and artist win when it has them: the title is set huge in
 * Hanzi, and some bundles' titles are romanised ("Yue Liang Dai Biao Wo De Xin");
 * the artist is the one of the recording we sing along to.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("A song that isn't ready still tunes in").
 */
import type { SongSummary } from "../api/client";
import { FALLBACK_PALETTE, type SongTheme } from "../theme/songThemes";

export type Entry = { id: string; title: string; artist: string; playable: boolean; theme: SongTheme };

/**
 * Songs the backend serves only as test fixtures, never shown on the record:
 * "demo" is a hand-written two-line 两只老虎 with no track.
 */
export const HIDDEN_SONGS: ReadonlySet<string> = new Set(["demo"]);

export function buildEntries(songs: SongSummary[], themes: Record<string, SongTheme>): Entry[] {
  songs = songs.filter((s) => !HIDDEN_SONGS.has(s.id));
  const served = songs.map((s) => {
    const theme = themes[s.id] ?? { palette: FALLBACK_PALETTE };
    return { id: s.id, title: theme.title ?? s.title, artist: theme.artist ?? s.artist, playable: true, theme };
  });
  const ids = new Set(songs.map((s) => s.id));
  const soon = Object.entries(themes)
    .filter(([id, t]) => !ids.has(id) && !HIDDEN_SONGS.has(id) && t.title)
    .map(([id, t]) => ({ id, title: t.title!, artist: t.artist ?? "", playable: false, theme: t }));
  return [...served, ...soon];
}
