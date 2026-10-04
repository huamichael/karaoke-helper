/**
 * The line screen's header fades in on pointer movement and out after 2.5 s of
 * stillness, unless it is held (controls open, a word being practiced) or the
 * pointer is over it. The cursor hides with it.
 *
 * hide() takes it away at once (E or a double-click closing the controls); for a
 * moment after that, pointer movement does not bring it back, so the jitter of
 * the double-click itself does not undo it.
 *
 * Owner: A. Spec: docs/design/ui.md §3.3 ("Header"), §5.3.1.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useLatest } from "./useLatest";

const STILL_MS = 2500;
const HIDE_GRACE_MS = 700;

export function useChrome(hold: boolean) {
  const [on, setOn] = useState(true);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const over = useRef(false);
  const quietUntil = useRef(0);
  const held = useLatest(hold);

  const fade = useCallback(function fade() {
    if (over.current || held.current) {
      timer.current = setTimeout(fade, 800);
      return;
    }
    setOn(false);
  }, [held]);

  const show = useCallback(() => {
    setOn(true);
    clearTimeout(timer.current);
    timer.current = setTimeout(fade, STILL_MS);
  }, [fade]);

  /** Pointer movement: bring the header back, unless it was just hidden on purpose. */
  const poke = useCallback(() => {
    if (performance.now() < quietUntil.current) return;
    show();
  }, [show]);

  const hide = useCallback(() => {
    clearTimeout(timer.current);
    quietUntil.current = performance.now() + HIDE_GRACE_MS;
    setOn(false);
  }, []);

  useEffect(() => {
    show();
    return () => clearTimeout(timer.current);
  }, [show]);

  // When the hold ends (controls closed with Aa, practice over), the header stays a moment, then fades;
  // after hide() it stays hidden.
  useEffect(() => {
    if (!hold) poke();
  }, [hold, poke]);

  const setOver = useCallback((v: boolean) => { over.current = v; }, []);
  return { on, poke, show, hide, setOver };
}
