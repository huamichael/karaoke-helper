/**
 * Three scraps cut from the song's own photo, overlapping the record's rim: a wide
 * torn piece held by tape, a narrow torn strip, and a round cut. Each shows an
 * enlarged detail of the photo (the theme's focus points), so the photo seems to
 * run onto the record. Positions and sizes come from logic/collage.ts.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("Collage where the record meets the photo").
 */
import { useEffect, useState, type CSSProperties } from "react";
import { SCRAPS, scrapBox, scrapPhotoSize } from "../../logic/collage";
import type { SongTheme } from "../../theme/songThemes";

const sizes = new Map<string, [number, number]>();

function usePhotoSize(src: string | undefined) {
  const [size, setSize] = useState(src ? sizes.get(src) : undefined);
  useEffect(() => {
    if (!src) return setSize(undefined);
    if (sizes.has(src)) return setSize(sizes.get(src));
    const im = new Image();
    im.onload = () => { sizes.set(src, [im.naturalWidth, im.naturalHeight]); setSize([im.naturalWidth, im.naturalHeight]); };
    im.src = src;
  }, [src]);
  return size;
}

type Props = { songId: string; theme: SongTheme; g: { cx: number; cy: number; R: number }; W: number; H: number };

export function Scraps({ songId, theme, g, W, H }: Props) {
  const size = usePhotoSize(theme.photo);
  if (!theme.photo) return null;
  return (
    <div className="scraps" key={songId}>
      {SCRAPS.map((sc) => {
        const b = scrapBox(sc, g);
        const poly = sc.poly.map(([x, y]) => `${x}% ${y}%`).join(",");
        const inner = sc.poly.map(([x, y]) => `${50 + (x - 50) * 0.93}% ${50 + (y - 50) * 0.91}%`).join(",");
        const focus = theme.focus?.[sc.i] ?? "50% 50%";
        const bg = size ? scrapPhotoSize(size, W, H, sc.zoom).map((v) => `${v.toFixed(0)}px`).join(" ") : "260%";
        return (
          <div key={sc.i} className="scrap" style={{ left: Math.round(b.x), top: Math.round(b.y), width: Math.round(b.w), height: Math.round(b.h), "--t": `rotate(${sc.rot}deg)` } as CSSProperties}>
            <div className="scrap-paper" style={{ clipPath: `polygon(${poly})` }} />
            <div className="scrap-img" style={{ clipPath: `polygon(${inner})`, backgroundImage: `url(${theme.photo})`, backgroundSize: bg, backgroundPosition: focus }} />
            {sc.tape && <i className="tape" style={{ left: `${sc.tape[0]}%`, top: sc.tape[1], transform: `rotate(${sc.tape[2]}deg)` }} />}
          </div>
        );
      })}
    </div>
  );
}
