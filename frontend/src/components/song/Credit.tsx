/**
 * Credits for the photograph (Unsplash) and the album cover, small, bottom right.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("Credits").
 */
import type { SongTheme } from "../../theme/songThemes";

export function Credit({ theme }: { theme: SongTheme }) {
  const photo = theme.photoCredit;
  const cover = theme.cover && theme.album;
  if (!photo && !cover) return null;
  return (
    <p className="credit">
      {photo && <>Photo: <a href={photo.url} target="_blank" rel="noopener noreferrer">{photo.name}</a>, Unsplash</>}
      {photo && cover && <i />}
      {cover && <>Cover: {theme.artist}《{theme.album}》{theme.year ? `, ${theme.year}` : ""}</>}
    </p>
  );
}
