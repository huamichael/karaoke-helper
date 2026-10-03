/**
 * Song screen: the song list and the mode choice.
 *
 * The user picks a song and, when VITE_SHOW_MODE_CHOICE is on, spoken or singing
 * accuracy, then starts at line 1.
 *
 * Owner: A. Spec: docs/tasks/frontend.md.
 */
import type { Mode } from "../api/client";
import type { Entry } from "../logic/songList";

type Props = { entries: Entry[]; selected: number; onSelect(i: number): void; onStart(mode: Mode): void; error: string | null };

export default function SongScreen({ entries, selected, onSelect, onStart, error }: Props) {
  const e = entries[selected];
  return (
    <section className="absolute inset-0 flex flex-col items-start justify-center gap-6 px-[7vw]">
      <h1 className="font-serif text-6xl font-extralight">{e?.title ?? "Karaoke Helper"}</h1>
      {error && <p className="note">{error}</p>}
      <ul className="flex gap-3">
        {entries.map((x, k) => (
          <li key={x.id}>
            <button className={`btn${k === selected ? " primary" : ""}`} onClick={() => onSelect(k)}>{x.title}</button>
          </li>
        ))}
      </ul>
      {e && <button className="btn primary" disabled={!e.playable} onClick={() => onStart("spoken")}>{e.playable ? `Sing ${e.title}` : "Coming soon"}</button>}
    </section>
  );
}
