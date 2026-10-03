/**
 * A glass pill whose width springs to its contents (the dock and the options pill).
 *
 * The motion-primitives toolbar pattern: measure the contents, animate the width
 * with a soft spring. Animating the width itself, rather than Motion's `layout`
 * scale transform, keeps the buttons' text from stretching mid-animation.
 *
 * Owner: A. Spec: docs/design/ui.md §3.3 ("Soft spring"), §3.4.
 */
import { motion, useReducedMotion } from "motion/react";
import { useLayoutEffect, useRef, useState, type ReactNode } from "react";

export const SOFT = { type: "spring", bounce: 0.1, duration: 0.3 } as const;

type Props = { className: string; innerClassName: string; contentKey: string; children: ReactNode; label?: string; border?: number };

export function MeasuredPill({ className, innerClassName, contentKey, children, label, border = 1 }: Props) {
  const inner = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState<number | null>(null);
  const reduced = useReducedMotion();

  useLayoutEffect(() => {
    const el = inner.current;
    if (!el) return;
    const measure = () => setWidth(el.offsetWidth + 2 * border);
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [contentKey, border]);

  return (
    <motion.div
      className={className}
      role={label ? "toolbar" : undefined}
      aria-label={label}
      initial={false}
      animate={width == null ? undefined : { width }}
      transition={reduced ? { duration: 0 } : SOFT}
    >
      <div ref={inner} key={contentKey} className={innerClassName}>
        {children}
      </div>
    </motion.div>
  );
}
