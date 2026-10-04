/**
 * The dock: the current step's actions when the controls are closed, every control
 * with a label when open, Word practice's actions while a word is practiced, and
 * the microphone prompt when it is needed. The actions come from logic/actions.ts.
 *
 * Owner: A. Spec: docs/design/ui.md §5.3 (dock column), §5.3.1, §5.4.
 */
import { useRef, type CSSProperties, type ReactNode } from "react";
import { useWidthMorph } from "../hooks/useWidthMorph";
import type { DockAction, DockActionId } from "../logic/actions";
import { PlayIcon, RetryIcon, StopIcon } from "./icons";
import { RecordButton, type Meter } from "./RecordButton";
import { Vinyl } from "./Vinyl";

type Props = {
  actions: DockAction[];
  spinning: boolean;
  recording: boolean;
  meter: Meter | null;
  onAction(id: DockActionId): void;
  /** Replaces the actions while the microphone is being set up. */
  prompt?: ReactNode;
  promptKey?: string;
};

const ICONS = { play: <PlayIcon />, stop: <StopIcon />, retry: <RetryIcon /> };

function Item({ a, i, spinning, recording, meter, onAction }: { a: DockAction; i: number } & Omit<Props, "actions" | "prompt" | "promptKey">) {
  const style = { "--i": i } as CSSProperties;
  const click = () => onAction(a.id);
  switch (a.kind) {
    case "vinyl":
      return (
        <button className={`vbtn${a.label ? " lbl" : ""}`} style={style} disabled={a.disabled} onClick={click}
          aria-label={spinning ? "Stop the line" : "Listen to the line"}>
          <Vinyl spinning={spinning}>{spinning ? <StopIcon /> : <PlayIcon />}</Vinyl>
          {a.label && <span className="txt">{a.label}</span>}
        </button>
      );
    case "record":
      return <RecordButton label={a.label ?? "Record"} recording={recording && a.label === "Stop"} primary={a.primary}
        disabled={a.disabled} meter={meter} onClick={click} style={style} />;
    case "round":
      return <button className="round" style={style} onClick={click} disabled={a.disabled} aria-label={a.label ?? undefined}><RetryIcon /></button>;
    case "busy":
      return <span className="busy" style={style}><span className="spinner" />{a.label}</span>;
    case "quiet":
    case "button":
      return (
        <button className={`btn${a.primary ? " primary" : ""}${a.kind === "quiet" ? " quiet" : ""}`} style={style} disabled={a.disabled} onClick={click}>
          {a.icon ? ICONS[a.icon] : a.id === "retry" ? <RetryIcon /> : null}
          {a.label}
        </button>
      );
  }
}

export function Dock({ actions, prompt, promptKey, ...rest }: Props) {
  const key = prompt ? `prompt:${promptKey}` : actions.map((a) => `${a.id}/${a.label}/${+a.disabled}/${+a.primary}`).join("|");
  const pill = useRef<HTMLDivElement>(null);
  // New buttons: the width springs to them as in the prototype (the soft spring) while they fade in.
  useWidthMorph(pill, key);
  return (
    <div ref={pill} className="dock" role="toolbar" aria-label="Controls">
      <div key={key} className="dock-row">
        {prompt ?? actions.map((a, i) => <Item key={a.id} a={a} i={i} {...rest} />)}
      </div>
    </div>
  );
}
