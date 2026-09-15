"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

type Theme = "light" | "dark" | "system";
type Resolved = "light" | "dark";

/** localStorage key shared with the no-flash script in the root layout. */
export const THEME_STORAGE_KEY = "bimaya-theme";

interface ThemeContextValue {
  /** The user's choice: an explicit theme, or "system" to follow the OS. */
  theme: Theme;
  /** The theme actually applied right now ("system" resolved against the OS). */
  resolvedTheme: Resolved;
  /** False until the client has read the stored preference (avoids UI jumps). */
  mounted: boolean;
  setTheme: (theme: Theme) => void;
  /** Flip between light and dark, pinning the opposite of what's showing. */
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function systemPrefersDark(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );
}

function readStoredTheme(): Theme {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === "light" || saved === "dark" || saved === "system") return saved;
  } catch {
    // Storage may be unavailable (private mode, blocked cookies) — fall through.
  }
  return "system";
}

function resolve(theme: Theme): Resolved {
  if (theme === "system") return systemPrefersDark() ? "dark" : "light";
  return theme;
}

function applyTheme(resolved: Resolved) {
  const el = document.documentElement;
  el.classList.toggle("dark", resolved === "dark");
  el.style.colorScheme = resolved;
}

// --- Module-level store -----------------------------------------------------
// The theme lives in external systems (localStorage + the OS media query), so
// we read it through useSyncExternalStore rather than mirroring it into state
// from an effect. SSR and the first client render share one fixed snapshot —
// the blocking script in the document has already applied the correct class —
// and the store reconciles to the real preference once subscribed.

type StoreState = { theme: Theme; resolvedTheme: Resolved; mounted: boolean };

// Returned by both the server and the first client render so hydration agrees.
const INITIAL_STATE: StoreState = {
  theme: "system",
  resolvedTheme: "light",
  mounted: false,
};

let state = INITIAL_STATE;
const listeners = new Set<() => void>();

function sync() {
  const theme = readStoredTheme();
  const resolvedTheme = resolve(theme);
  if (
    state.mounted &&
    state.theme === theme &&
    state.resolvedTheme === resolvedTheme
  ) {
    return; // Unchanged — keep the snapshot referentially stable.
  }
  state = { theme, resolvedTheme, mounted: true };
  applyTheme(resolvedTheme);
  for (const listener of listeners) listener();
}

function writeTheme(next: Theme) {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, next);
  } catch {
    // Persisting is best-effort; the choice still applies for this session.
  }
  sync();
}

let started = false;
function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  if (!started) {
    started = true;
    // The first subscriber wires up the live sources and pulls the real value.
    window.addEventListener("storage", sync);
    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", sync);
    sync();
  }
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): StoreState {
  return state;
}

function getServerSnapshot(): StoreState {
  return INITIAL_STATE;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const store = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const setTheme = useCallback((next: Theme) => writeTheme(next), []);
  const toggleTheme = useCallback(() => {
    writeTheme(state.resolvedTheme === "dark" ? "light" : "dark");
  }, []);

  const value = useMemo(
    () => ({
      theme: store.theme,
      resolvedTheme: store.resolvedTheme,
      mounted: store.mounted,
      setTheme,
      toggleTheme,
    }),
    [store.theme, store.resolvedTheme, store.mounted, setTheme, toggleTheme],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
