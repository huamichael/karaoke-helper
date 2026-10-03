/**
 * PhotoBackdrop and DynamicBackground: every song's photograph, stacked and
 * crossfaded by weight. Sharp on the song screen, blurred into the line screen's
 * background (the `singing` class on the app). A song without a photo falls back
 * to blurred blobs in its c1–c3 over c0.
 *
 * The song screen's record writes the weights every frame through the handle, so
 * turning it never re-renders React.
 *
 * Owner: A. Spec: docs/design/ui.md §3.1 ("Background"), §6.
 */
import { forwardRef, useImperativeHandle, useLayoutEffect, useRef } from "react";
import type { Entry } from "../logic/songList";

export type BackdropHandle = { setWeights(w: number[]): void };

export const Backdrop = forwardRef<BackdropHandle, { entries: Entry[]; selected: number }>(function Backdrop({ entries, selected }, ref) {
  const photos = useRef<(HTMLDivElement | null)[]>([]);
  const blobs = useRef<HTMLDivElement>(null);

  const setWeights = (w: number[]) => {
    let blobWeight = 0;
    entries.forEach((e, k) => {
      const el = photos.current[k], x = w[k] ?? 0;
      if (!e.theme.photo) blobWeight += x;
      if (!el) return;
      el.style.opacity = x.toFixed(3);
      el.style.filter = x > 0.01 && x < 0.99 ? `blur(${((1 - x) * 14).toFixed(1)}px)` : "";
    });
    if (blobs.current) blobs.current.style.opacity = blobWeight.toFixed(3);
  };

  useImperativeHandle(ref, () => ({ setWeights }));
  // Until the record reports in, show the selected song. Later renders leave the weights alone.
  const shown = useRef(false);
  useLayoutEffect(() => {
    if (shown.current || !entries.length) return;
    shown.current = true;
    setWeights(entries.map((_, k) => (k === selected ? 1 : 0)));
  });

  return (
    <div className="backdrop" aria-hidden>
      <div ref={blobs}>
        <div className="blob b1" /><div className="blob b2" /><div className="blob b3" />
      </div>
      <div className="photos">
        {entries.map((e, k) => (
          <div key={e.id} ref={(el) => { photos.current[k] = el; }} className="photo"
            style={e.theme.photo ? { backgroundImage: `url(${e.theme.photo})` } : undefined} />
        ))}
      </div>
    </div>
  );
});
