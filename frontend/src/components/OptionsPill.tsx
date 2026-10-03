/**
 * The options pill: "Aa" when closed. Opening it grows the pill leftwards into the
 * Pinyin and Translation switches, "Aa" turns into ✕, and the dock grows into every
 * control at the same time. One switch, one look.
 *
 * Owner: A. Spec: docs/design/ui.md §5.3.1.
 */
import type { CSSProperties } from "react";
import { CloseIcon } from "./icons";
import { MeasuredPill } from "./MeasuredPill";

type Props = {
  open: boolean;
  showPinyin: boolean;
  showTranslation: boolean;
  onToggleOpen(): void;
  onTogglePinyin(): void;
  onToggleTranslation(): void;
};

export function OptionsPill({ open, showPinyin, showTranslation, onToggleOpen, onTogglePinyin, onToggleTranslation }: Props) {
  return (
    <MeasuredPill className="opts" innerClassName="opts-inner" contentKey={open ? "open" : "closed"}>
      {open && (
        <div className="opts-row">
          <button className="chip" role="switch" aria-checked={showPinyin} onClick={onTogglePinyin} style={{ "--i": 0 } as CSSProperties}><i />Pinyin</button>
          <button className="chip" role="switch" aria-checked={showTranslation} onClick={onToggleTranslation} style={{ "--i": 1 } as CSSProperties}><i />Translation</button>
        </div>
      )}
      <button className="opts-btn" onClick={onToggleOpen} aria-expanded={open} aria-label={open ? "Hide controls and options" : "Show every control and option"}>
        <span className="aa">Aa</span>
        <CloseIcon />
      </button>
    </MeasuredPill>
  );
}
