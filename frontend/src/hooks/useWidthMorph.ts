/**
 * The prototype's morphWidth: when `key` changes the element's contents, its
 * width springs from what was on screen to the new natural width (the soft
 * spring, held `extraMs` longer), then goes back to auto. Width, not a scale
 * transform, so the text inside never stretches.
 *
 * The width on screen is kept by a ResizeObserver, so it is right even when a
 * font arrives late; a change in mid-flight starts from where the pill is.
 *
 * Owner: A. Spec: docs/design/ui.md §3.3 ("Soft spring").
 */
import { useReducedMotion } from "motion/react";
import { useLayoutEffect, useRef, type RefObject } from "react";
import { linearEasing, SOFT_SPRING } from "../logic/spring";

export function useWidthMorph(ref: RefObject<HTMLElement | null>, key: unknown, extraMs = 0) {
  const shown = useRef<number | null>(null);
  const anim = useRef<Animation | null>(null);
  const reduced = useReducedMotion();

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(() => { if (!anim.current) shown.current = el.getBoundingClientRect().width; });
    ro.observe(el);
    return () => { ro.disconnect(); anim.current?.cancel(); };
  }, [ref]);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const from = anim.current ? el.getBoundingClientRect().width : shown.current;
    anim.current?.cancel();
    anim.current = null;
    const to = el.getBoundingClientRect().width;
    shown.current = to;
    if (from == null || reduced || Math.abs(to - from) <= 2) return;
    const a = el.animate([{ width: `${from}px` }, { width: `${to}px` }], { duration: SOFT_SPRING.durationMs + extraMs, easing: linearEasing(SOFT_SPRING.points) });
    anim.current = a;
    a.finished.then(() => { if (anim.current === a) anim.current = null; }, () => {});
  }, [ref, key, extraMs, reduced]);
}
