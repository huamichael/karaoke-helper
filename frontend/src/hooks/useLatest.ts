/**
 * A ref that always holds the latest value, for event listeners and async
 * callbacks that must not read a stale render.
 *
 * Owner: A.
 */
import { useLayoutEffect, useRef } from "react";

export function useLatest<T>(value: T) {
  const ref = useRef(value);
  useLayoutEffect(() => {
    ref.current = value;
  });
  return ref;
}
