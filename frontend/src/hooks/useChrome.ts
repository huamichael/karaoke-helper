/**
 * The line screen's header fades in on pointer movement and out after 2.5 s of
 * stillness, unless it is held (controls open, a word being practised) or the
 * pointer is over it. The cursor hides with it.
 *
 * Owner: A. Spec: docs/design/ui.md §3.3 ("Header").
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useLatest } from "./useLatest";

export function useChrome(hold: boolean) {
  const [on, setOn] = useState(true);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const over = useRef(false);
  const held = useLatest(hold);

  const hide = useCallback(function hide() {
    if (over.current || held.current) {
      timer.current = setTimeout(hide, 800);
      return;
    }
    setOn(false);
  }, [held]);

  const poke = useCallback(() => {
    setOn(true);
    clearTimeout(timer.current);
    timer.current = setTimeout(hide, 2500);
  }, [hide]);

  useEffect(() => {
    poke();
    return () => clearTimeout(timer.current);
  }, [poke]);

  useEffect(() => {
    if (!hold) poke();
  }, [hold, poke]);

  const setOver = useCallback((v: boolean) => { over.current = v; }, []);
  return { on, poke, setOver };
}
