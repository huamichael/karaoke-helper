/**
 * SongRecord: the song wheel as a huge stylized record, 45° per song. The songs
 * ride its groove band, three in view, looping, each name tilted to the record's
 * angle as if printed on it.
 *
 * The position is unbounded and shown modulo the song count (logic/recordWheel.ts).
 * It follows the wheel, trackpad or a drag continuously and settles on a song with
 * a spring when the gesture ends; ↑ ↓ ← → and clicking a song turn it too. While
 * the record plays, the platter turns at 30° a second, spinning up and down
 * (logic/turntable.ts). The cover button, the tonearm and the sound cap ride
 * inside the dial as children, so they leave with it.
 *
 * Owner: A. Spec: docs/design/ui.md §3.3 ("Spinning the record"), §5.1, §6.
 */
import { useReducedMotion } from "motion/react";
import { forwardRef, useEffect, useImperativeHandle, useLayoutEffect, useRef, useState, type PointerEvent, type ReactNode } from "react";
import { useLatest } from "../../hooks/useLatest";
import {
  crossfadeWeights, dragSettle, DRAG_PX_PER_SONG, labelSlots, mod, selectedIndex, STEP_DEG, stepSpring, wheelSettle, WHEEL_PX_PER_SONG,
  type wheelGeometry,
} from "../../logic/recordWheel";
import type { Entry } from "../../logic/songList";
import { PLATTER_SPEED, platterStep } from "../../logic/turntable";
import { discTransform, RecordDisc } from "./RecordDisc";

export type SongRecordHandle = { wheel(e: WheelEvent): void; step(dir: 1 | -1): void };

type Props = {
  entries: Entry[];
  g: ReturnType<typeof wheelGeometry>;
  initial: number;
  /** The platter turns: the record is playing, or still slowing down. */
  spinning: boolean;
  /** "Playing a preview" under the selected song. */
  previewing: boolean;
  onTurn(u: number): void;
  onSelect(index: number): void;
  onSettle(index: number): void;
  onGestureStart(): void;
  /** Drawn on the record, under the song names: the collage scraps. */
  between?: ReactNode;
  /** Drawn over everything in the dial: the cover button, the tonearm, the sound cap. */
  children?: ReactNode;
};

type Drag = { id: number; y0: number; u0: number; lastY: number; lastT: number; v: number; moved: boolean };

export const SongRecord = forwardRef<SongRecordHandle, Props>(function SongRecord(
  { entries, g, initial, spinning, previewing, onTurn, onSelect, onSettle, onGestureStart, between, children }, ref,
) {
  const n = Math.max(1, entries.length);
  const reduced = useReducedMotion();
  const [u, setU] = useState(initial);
  const [grabbing, setGrabbing] = useState(false);
  const dial = useRef<HTMLDivElement>(null);
  const st = useRef({ u: initial, v: 0, target: initial, raf: 0, last: 0, wheeling: false, wheelStart: 0, raw: 0, wheelT: 0 as ReturnType<typeof setTimeout> | 0, drag: null as Drag | null });
  const cb = useLatest({ onTurn, onSelect, onSettle, onGestureStart, n, reduced });

  const set = (x: number) => {
    st.current.u = x;
    setU(x);
    cb.current.onTurn(x);
  };

  const sel = selectedIndex(u, n);
  useEffect(() => { cb.current.onSelect(sel); }, [sel, cb]);
  useEffect(() => { cb.current.onTurn(st.current.u); }, [cb]);

  const stopSpring = () => {
    cancelAnimationFrame(st.current.raf);
    st.current.raf = 0;
    st.current.v = 0;
  };

  const frame = (now: number) => {
    const s = st.current;
    const dt = Math.min(0.032, (now - s.last) / 1000);
    s.last = now;
    const r = stepSpring(s, s.target, dt);
    s.v = r.v;
    set(r.u);
    if (r.done) {
      s.raf = 0;
      cb.current.onSettle(mod(s.target, cb.current.n));
    } else s.raf = requestAnimationFrame(frame);
  };

  const springTo = (t: number) => {
    const s = st.current;
    s.target = t;
    if (cb.current.reduced) {
      stopSpring();
      set(t);
      cb.current.onSettle(mod(t, cb.current.n));
      return;
    }
    if (!s.raf) {
      s.last = performance.now();
      s.raf = requestAnimationFrame(frame);
    }
  };

  const turnTo = (t: number) => {
    cb.current.onGestureStart();
    springTo(t);
  };

  useEffect(() => () => { cancelAnimationFrame(st.current.raf); clearTimeout(st.current.wheelT || undefined); }, []);

  useImperativeHandle(ref, () => ({
    wheel(e) {
      if (e.ctrlKey) return;
      e.preventDefault();
      const s = st.current;
      const d = Math.abs(e.deltaY) >= Math.abs(e.deltaX) ? e.deltaY : e.deltaX;
      if (!s.wheeling) {
        s.wheeling = true;
        stopSpring();
        s.wheelStart = Math.round(s.u);
        s.raw = s.u;
        cb.current.onGestureStart();
      }
      s.raw += (d * (e.deltaMode === 1 ? 16 : 1)) / WHEEL_PX_PER_SONG;
      set(s.raw);
      clearTimeout(s.wheelT || undefined);
      s.wheelT = setTimeout(() => {
        s.wheeling = false;
        springTo(wheelSettle(s.wheelStart, s.raw));
      }, 140);
    },
    step(dir) {
      const s = st.current;
      turnTo(Math.round(s.raf ? s.target : s.u) + dir);
    },
  }));

  // The platter: spins up when the record plays, slows to a stop after the arm is back on its rest.
  // The disc's angle is the wheel's position plus the platter's turn. It is written straight to the
  // disc, every frame while the platter turns, not rendered: a render a frame cost far more than the turn.
  const platter = useRef({ speed: 0, angle: 0 });
  const spinEl = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    if (spinEl.current) spinEl.current.style.transform = discTransform(u * STEP_DEG + platter.current.angle);
  }, [u]);
  useEffect(() => {
    const target = spinning && !reduced ? PLATTER_SPEED : 0;
    let last = performance.now(), raf = 0;
    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000), p = platter.current;
      last = now;
      p.speed = platterStep(p.speed, target, dt);
      if (p.speed) {
        p.angle += p.speed * dt;
        if (spinEl.current) spinEl.current.style.transform = discTransform(st.current.u * STEP_DEG + p.angle);
      }
      if (p.speed || target) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [spinning, reduced]);

  const onPointerDown = (e: PointerEvent) => {
    if ((e.target as HTMLElement).closest(".arm-sound")) return;
    st.current.drag = { id: e.pointerId, y0: e.clientY, u0: st.current.u, lastY: e.clientY, lastT: performance.now(), v: 0, moved: false };
    stopSpring();
  };
  const onPointerMove = (e: PointerEvent) => {
    const d = st.current.drag;
    if (!d || e.pointerId !== d.id) return;
    if (!d.moved && Math.abs(e.clientY - d.y0) > 4) {
      d.moved = true;
      dial.current?.setPointerCapture(e.pointerId);
      setGrabbing(true);
      cb.current.onGestureStart();
    }
    if (!d.moved) return;
    const now = performance.now();
    d.v = ((d.lastY - e.clientY) / DRAG_PX_PER_SONG / Math.max(1, now - d.lastT)) * 1000;
    d.lastY = e.clientY;
    d.lastT = now;
    set(d.u0 + (d.y0 - e.clientY) / DRAG_PX_PER_SONG);
  };
  const onPointerUp = (e: PointerEvent) => {
    const d = st.current.drag;
    if (!d || e.pointerId !== d.id) return;
    st.current.drag = null;
    setGrabbing(false);
    // a drag settles with its speed; a plain press resumes wherever the record was heading
    springTo(d.moved ? dragSettle(st.current.u, d.v) : Math.round(st.current.target));
  };

  const weights = crossfadeWeights(u, n);
  const selected = entries[sel];
  const t = selected?.theme;
  const ring = selected ? `${selected.artist}　${t?.album ?? ""}　${t?.year ?? ""}　${selected.title}　Lotus Roots　`.replace(/(　)+/g, "　") : "";

  return (
    <div ref={dial} className={`dial${grabbing ? " grabbing" : ""}`} role="listbox" aria-label="Songs"
      onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp}>
      <RecordDisc entries={entries} weights={weights} g={g} ring={ring} spinRef={spinEl} />
      {between}
      {labelSlots(u, n, g).map((s) => {
        const e = entries[s.song];
        if (!e) return null;
        const size = Math.min(24, Math.floor((g.nameMax - 20) / [...e.title].length));
        return (
          <button key={s.key} className="dn" role="option" aria-selected={s.selected}
            style={{
              maxWidth: Math.round(g.nameMax), opacity: +s.opacity.toFixed(3),
              transform: `translate(${s.x.toFixed(1)}px, ${s.y.toFixed(1)}px) translate(-50%, -50%) rotate(${s.tiltDeg.toFixed(2)}deg) scale(${s.scale.toFixed(3)})`,
            }}
            onClick={() => turnTo(s.key)}>
            <span className="dn-n">{String(s.song + 1).padStart(2, "0")}</span>
            <span className="dn-t" style={{ fontSize: size }}>{e.title}</span>
            <span className="dn-a">{e.artist}{e.playable ? "" : ", coming soon"}</span>
            {s.selected && previewing && <span className="dn-p"><span className="eq" aria-hidden><i /><i /><i /></span>Playing a preview</span>}
          </button>
        );
      })}
      <i className="needle" style={{ left: g.cx - g.R + 22, top: g.cy }} />
      {children}
    </div>
  );
});
