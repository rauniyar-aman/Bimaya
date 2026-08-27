"use client";

/**
 * Compare selection, kept in `localStorage` so it survives navigation and can
 * be shared as a `/compare?ids=` link. Capped at four policies to match the
 * backend's compare limit. A custom event keeps every mounted button in sync.
 */
const KEY = "bimaya:compare";
const EVENT = "bimaya:compare-changed";
export const MAX_COMPARE = 4;

function read(): number[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((v): v is number => typeof v === "number").slice(0, MAX_COMPARE);
  } catch {
    return [];
  }
}

function write(ids: number[]): void {
  window.localStorage.setItem(KEY, JSON.stringify(ids));
  window.dispatchEvent(new CustomEvent(EVENT));
}

export function getCompareIds(): number[] {
  return read();
}

/** Add or remove an id; returns the new list. No-op add once full. */
export function toggleCompareId(id: number): number[] {
  const ids = read();
  const next = ids.includes(id)
    ? ids.filter((v) => v !== id)
    : ids.length >= MAX_COMPARE
      ? ids
      : [...ids, id];
  write(next);
  return next;
}

export function removeCompareId(id: number): number[] {
  const next = read().filter((v) => v !== id);
  write(next);
  return next;
}

export function setCompareIds(ids: number[]): number[] {
  const next = ids.slice(0, MAX_COMPARE);
  write(next);
  return next;
}

export function clearCompare(): void {
  write([]);
}

/** Subscribe to changes from any tab/component; returns an unsubscribe fn. */
export function onCompareChange(listener: () => void): () => void {
  window.addEventListener(EVENT, listener);
  window.addEventListener("storage", listener);
  return () => {
    window.removeEventListener(EVENT, listener);
    window.removeEventListener("storage", listener);
  };
}
