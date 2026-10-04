/**
 * The record itself: a torn-paper cut-out pasted onto the photograph. Under a
 * torn edge, a fringe of off-white paper with a paper shadow; on it, fine grooves,
 * two track gaps, the album-cover label with a ring of small text, and a sheen in
 * the song's own colours that stays still while the grooves turn.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("The record", "Collage where the record meets the photo").
 */
import type { CSSProperties, Ref } from "react";
import { tornMask } from "../../logic/collage";
import type { Entry } from "../../logic/songList";

const BODY_MASK = tornMask(4, 476, 26);
const PAPER_MASK = tornMask(9, 492, 34);
const mask = (m: string): CSSProperties => ({ WebkitMaskImage: m, maskImage: m });

export const discTransform = (deg: number) => `rotate(${deg.toFixed(2)}deg)`;

type Props = {
  entries: Entry[]; weights: number[]; g: { cx: number; cy: number; R: number; rl: number }; ring: string;
  /** The turning part. Its owner turns it by writing discTransform, every frame while it plays, without a render. */
  spinRef: Ref<HTMLDivElement>;
};

export function RecordDisc({ entries, weights, g, ring, spinRef }: Props) {
  return (
    <div className="disc" style={{ width: 2 * g.R, height: 2 * g.R, left: g.cx - g.R, top: g.cy - g.R, "--rl": `${g.rl}px` } as CSSProperties}>
      <div className="disc-paper"><i style={mask(PAPER_MASK)} /></div>
      <div className="disc-body" style={mask(BODY_MASK)}>
        <div ref={spinRef} className="disc-spin">
          <div className="disc-grooves" />
          <svg className="disc-ring" viewBox="0 0 200 200" aria-hidden>
            <defs><path id="ringPath" d="M100,100 m-90,0 a90,90 0 1,1 180,0 a90,90 0 1,1 -180,0" /></defs>
            <text><textPath href="#ringPath" textLength="560" lengthAdjust="spacing">{ring + ring}</textPath></text>
          </svg>
          <div className="disc-label">
            {entries.map((e, k) => e.theme.cover && (
              <div key={e.id} className="cover" style={{ backgroundImage: `url(${e.theme.cover})`, opacity: +(weights[k] ?? 0).toFixed(3) }} />
            ))}
          </div>
          <i className="disc-hole" />
        </div>
        <div className="disc-sheen" />
      </div>
    </div>
  );
}
