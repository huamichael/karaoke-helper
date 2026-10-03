/**
 * Tonearm: the three.js arm over the record (scene in ./tonearm/arm.ts, loaded on
 * demand). Arm on the record = playing; arm on its rest = stopped. Clicking the
 * arm, its base or its rest plays or stops the record; it lights up under the
 * pointer. Moves asked for before three.js has loaded wait for it; if WebGL is
 * unavailable they resolve at once, so the record still plays without an arm.
 *
 * Owner: A. Spec: docs/design/ui.md §5.1 ("The tonearm", "It behaves like a real turntable"), §6.
 */
import { forwardRef, useEffect, useImperativeHandle, useRef, type RefObject } from "react";
import type { ArmPlace, TonearmScene } from "./tonearm/arm";

export type { ArmPlace };
export type TonearmHandle = { go(where: ArmPlace): Promise<boolean> };

type Props = {
  g: { cx: number; cy: number; R: number };
  width: number;
  height: number;
  accent: string;
  /** The screen whose clicks the arm takes where it is drawn. */
  host: RefObject<HTMLElement | null>;
  onToggle(): void;
};

export const Tonearm = forwardRef<TonearmHandle, Props>(function Tonearm({ g, width, height, accent, host, onToggle }, ref) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const arm = useRef<TonearmScene | null>(null);
  const failed = useRef(false);
  const pending = useRef<{ where: ArmPlace; resolve(ok: boolean): void } | null>(null);
  const view = useRef({ g, width, height, accent, onToggle });
  view.current = { g, width, height, accent, onToggle };

  useImperativeHandle(ref, () => ({
    go(where) {
      if (arm.current) return arm.current.go(where);
      if (failed.current) return Promise.resolve(true);
      pending.current?.resolve(false);
      return new Promise((resolve) => { pending.current = { where, resolve }; });
    },
  }), []);

  // Load three.js and build the scene.
  useEffect(() => {
    let alive = true;
    const flush = () => {
      const p = pending.current;
      pending.current = null;
      if (p) (arm.current ? arm.current.go(p.where) : Promise.resolve(true)).then(p.resolve);
    };
    const giveUp = setTimeout(() => { if (!arm.current) { failed.current = true; flush(); } }, 5000);
    import("./tonearm/arm").then(
      (m) => {
        if (!alive || !canvas.current) return;
        try {
          const v = view.current;
          arm.current = m.createTonearm(canvas.current, v.accent);
          arm.current.layout(v.g, v.width, v.height);
        } catch {
          failed.current = true; // no WebGL: the record plays without an arm
        }
        flush();
      },
      () => { failed.current = true; flush(); },
    );
    return () => {
      alive = false;
      clearTimeout(giveUp);
      arm.current?.dispose();
      arm.current = null;
    };
  }, []);

  useEffect(() => { arm.current?.layout(g, width, height); }, [g, width, height]);
  useEffect(() => { arm.current?.setAccent(accent); }, [accent]);

  // The arm is drawn above everything on the right, so wherever it is visible it takes the click.
  useEffect(() => {
    const el = host.current;
    if (!el) return;
    let hover = false;
    const onCap = (e: Event) => (e.target as HTMLElement).closest?.(".arm-sound");
    const swallowClick = (e: MouseEvent) => { e.stopPropagation(); e.preventDefault(); };
    const down = (e: PointerEvent) => {
      if (onCap(e) || !arm.current?.hit(e.clientX, e.clientY)) return;
      e.stopImmediatePropagation();
      e.preventDefault();
      el.addEventListener("click", swallowClick, { capture: true, once: true });
      view.current.onToggle();
    };
    const move = (e: PointerEvent) => {
      const on = !onCap(e) && !!arm.current?.hit(e.clientX, e.clientY);
      if (on === hover) return;
      hover = on;
      el.classList.toggle("on-arm", on);
      arm.current?.setHover(on);
    };
    el.addEventListener("pointerdown", down, true);
    el.addEventListener("pointermove", move);
    return () => {
      el.removeEventListener("pointerdown", down, true);
      el.removeEventListener("pointermove", move);
      el.classList.remove("on-arm");
    };
  }, [host]);

  return <canvas ref={canvas} className="arm-canvas" aria-hidden />;
});
