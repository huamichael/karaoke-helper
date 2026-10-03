/**
 * The line screen's header: back, the song title, "N / M", the mode badge, and the
 * options pill. It has no bar; it fades when the pointer is still (see useChrome).
 *
 * Owner: A. Spec: docs/tasks/frontend.md ("Header"), docs/design/ui.md §4.2–4.3.
 */
import type { ReactNode } from "react";
import { BackIcon } from "./icons";

type Props = {
  backLabel: string;
  onBack(): void;
  title: string;
  position: string;
  badge: string;
  onHover(over: boolean): void;
  children: ReactNode;
};

export function TopBar({ backLabel, onBack, title, position, badge, onHover, children }: Props) {
  return (
    <header className="topbar" onPointerEnter={() => onHover(true)} onPointerLeave={() => onHover(false)}>
      <button className="back" onClick={onBack}><BackIcon /><span>{backLabel}</span></button>
      <div className="now"><span className="t">{title}</span><span className="n">{position}</span></div>
      <span className="badge">{badge}</span>
      <div className="spacer" />
      {children}
    </header>
  );
}
