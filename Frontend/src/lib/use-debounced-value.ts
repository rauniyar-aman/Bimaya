"use client";

import { useEffect, useState } from "react";

/**
 * Returns `value` after it has stayed unchanged for `delay` ms — so a search
 * box can update on every keystroke while the API is only hit once the user
 * pauses. The pending timer is cleared on each change and on unmount.
 */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}
