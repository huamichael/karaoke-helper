/**
 * Short hints at the bottom of the screen. Call toast("…") from anywhere; <Toaster/> shows it.
 *
 * Owner: A. Spec: docs/design/ui.md §5.3.1 ("First line of a session"), §5.3.2.
 */
import { useEffect, useState } from "react";

type Msg = { text: string; ms: number; id: number };
let listener: ((m: Msg) => void) | null = null;
let seq = 0;

export function toast(text: string, ms = 2600) {
  listener?.({ text, ms, id: ++seq });
}

export function Toaster() {
  const [msg, setMsg] = useState<Msg | null>(null);
  const [on, setOn] = useState(false);
  useEffect(() => {
    listener = (m) => { setMsg(m); setOn(true); };
    return () => { listener = null; };
  }, []);
  useEffect(() => {
    if (!msg) return;
    const t = setTimeout(() => setOn(false), msg.ms);
    return () => clearTimeout(t);
  }, [msg]);
  return <div className={`toast${on ? " on" : ""}`} role="status">{msg?.text}</div>;
}
