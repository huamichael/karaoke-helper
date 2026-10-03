/**
 * The scrolling list of lyric lines. The active line sits at the vertical centre.
 *
 * Changing line is FLIP: measure every line, change the layout, then spring each
 * line from where it was, so the active line's growth and the list's movement
 * animate together and no other line jumps. On touch the list follows the finger
 * and stretches a little past the first and last line.
 *
 * Owner: A. Spec: docs/design/ui.md §3.3 ("Changing line", "Swipe"), §5.3.2.
 */
import { forwardRef, useCallback, useImperativeHandle, useLayoutEffect, useRef, type ReactNode, type MouseEvent, type PointerEvent as ReactPointerEvent } from "react";
import { flushSync } from "react-dom";
import { touchFollow, touchStep, type Step } from "../logic/lineSwipe";
import { LINE_SPRING, linearEasing } from "../logic/spring";

export type LyricListHandle = {
  /** Apply a change that moves the active line, animating every line from where it was. */
  flip(mutate: () => void): void;
  /** Refused: the active line nudges 8px and settles. */
  nudge(dir: Step): void;
  /** Past the first or last line: the list stretches and springs back. */
  bounce(dir: Step): void;
};

type Props = {
  activeIndex: number;
  className?: string;
  /** A touch swipe ended past the threshold. */
  onTouchStep(dir: Step): void;
  locked: boolean;
  lineCount: number;
  onClickCapture?(e: MouseEvent): void;
  children: ReactNode;
};

const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const LINE_EASE = linearEasing(LINE_SPRING.points);

export const LyricList = forwardRef<LyricListHandle, Props>(function LyricList(
  { activeIndex, className, onTouchStep, locked, lineCount, onClickCapture, children }, ref,
) {
  const viewport = useRef<HTMLDivElement>(null);
  const track = useRef<HTMLDivElement>(null);
  const drag = useRef<{ id: number; y0: number; base: number; lastY: number; lastT: number; v: number } | null>(null);

  const activeWords = useCallback(() => track.current?.children[activeIndex]?.querySelector<HTMLElement>(".words") ?? null, [activeIndex]);

  const targetY = useCallback(() => {
    const w = activeWords(), vp = viewport.current;
    return w && vp ? Math.round(vp.clientHeight * 0.5 - (w.offsetTop + w.offsetHeight / 2)) : 0;
  }, [activeWords]);

  const anchor = useCallback(() => {
    if (track.current && !drag.current) track.current.style.transform = `translateY(${targetY()}px)`;
  }, [targetY]);

  // Re-anchor after every render and on resize; running FLIP animations are left alone.
  useLayoutEffect(anchor);
  useLayoutEffect(() => {
    window.addEventListener("resize", anchor);
    return () => window.removeEventListener("resize", anchor);
  }, [anchor]);

  const wordsOf = () => [...(track.current?.children ?? [])].map((l) => l.querySelector<HTMLElement>(".words"));

  useImperativeHandle(ref, () => ({
    flip(mutate) {
      const els = wordsOf();
      const go = !reduced() && els.length > 0;
      const before = go ? els.map((w) => w?.getBoundingClientRect() ?? null) : [];
      els.forEach((w) => w?.getAnimations().forEach((a) => a.cancel()));
      track.current?.getAnimations().forEach((a) => a.cancel());
      flushSync(mutate);
      if (!go) return;
      // the layout effect has re-anchored the track by now; animate each line from its old box
      wordsOf().forEach((w, k) => {
        const a = before[k], b = w?.getBoundingClientRect();
        if (!w || !a || !b || !a.width || !b.width) return;
        const dx = a.left + a.width / 2 - (b.left + b.width / 2), dy = a.top + a.height / 2 - (b.top + b.height / 2), s = a.width / b.width;
        if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5 && Math.abs(s - 1) < 0.005) return;
        w.animate([{ transform: `translate(${dx}px, ${dy}px) scale(${s})` }, { transform: "none" }], { duration: LINE_SPRING.durationMs, easing: LINE_EASE });
      });
    },
    nudge(dir) {
      if (reduced()) return;
      activeWords()?.animate([{ transform: "none" }, { transform: `translateY(${-dir * 8}px)` }, { transform: "none" }], { duration: 380, easing: "cubic-bezier(.3,.7,.4,1)" });
    },
    bounce(dir) {
      if (reduced() || !track.current) return;
      const y = targetY();
      track.current.animate([{ transform: `translateY(${y}px)` }, { transform: `translateY(${y - dir * 30}px)` }, { transform: `translateY(${y}px)` }], { duration: 460, easing: "cubic-bezier(.3,.7,.4,1)" });
    },
  }), [activeWords, targetY]);

  // Touch: the list follows the finger; release past 48px or with a flick to move one line.
  const onPointerDown = (e: ReactPointerEvent) => {
    if (e.pointerType !== "touch") return;
    drag.current = { id: e.pointerId, y0: e.clientY, base: targetY(), lastY: e.clientY, lastT: performance.now(), v: 0 };
    track.current?.getAnimations().forEach((a) => a.cancel());
    viewport.current?.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: ReactPointerEvent) => {
    const d = drag.current;
    if (!d || e.pointerId !== d.id || !track.current) return;
    const now = performance.now();
    d.v = (e.clientY - d.lastY) / Math.max(1, now - d.lastT);
    d.lastY = e.clientY;
    d.lastT = now;
    const dy = e.clientY - d.y0, dir = dy < 0 ? 1 : -1, j = activeIndex + dir;
    track.current.style.transform = `translateY(${d.base + touchFollow(dy, { locked, atEnd: j < 0 || j >= lineCount })}px)`;
  };
  const onPointerUp = (e: ReactPointerEvent) => {
    const d = drag.current;
    if (!d || e.pointerId !== d.id || !track.current) return;
    drag.current = null;
    const step = touchStep(e.clientY - d.y0, d.v);
    const from = track.current.style.transform;
    track.current.style.transform = `translateY(${d.base}px)`;
    const moves = step !== 0 && !locked && activeIndex + step >= 0 && activeIndex + step < lineCount;
    if (!moves && !reduced()) track.current.animate([{ transform: from }, { transform: `translateY(${d.base}px)` }], { duration: LINE_SPRING.durationMs, easing: LINE_EASE });
    if (step !== 0) onTouchStep(step);
  };

  return (
    <div className="viewport" ref={viewport} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp} onClickCapture={onClickCapture}>
      <div className={`track${className ? ` ${className}` : ""}`} ref={track}>{children}</div>
    </div>
  );
});
