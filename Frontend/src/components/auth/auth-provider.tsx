"use client";

/**
 * Holds the signed-in user for the whole app.
 *
 * The access token lives in memory only — never in localStorage — so an XSS bug
 * cannot lift a token that outlives the tab. Persistence comes from the
 * httpOnly refresh cookie, which is exchanged for a new access token on load
 * and whenever a request comes back 401.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { ApiError, apiFetch, type ApiFetchOptions, type AuthUser } from "@/lib/api";
import { session } from "@/lib/auth";

export type AuthStatus = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  user: AuthUser | null;
  status: AuthStatus;
  isAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<AuthUser>;
  completeVerification: (email: string, code: string) => Promise<AuthUser>;
  signOut: () => Promise<void>;
  /**
   * True once if the signed-out state came from the user pressing sign out
   * rather than from a session that died. Reading it clears it.
   */
  consumeSignOutIntent: () => boolean;
  /** Re-read the user from the API (after a profile update, say). */
  reloadUser: () => Promise<void>;
  /** Call a backend endpoint as the signed-in user, refreshing on 401. */
  authFetch: <T>(path: string, options?: ApiFetchOptions) => Promise<T>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  // Kept in a ref as well so `authFetch` always reads the newest token without
  // being re-created on every refresh.
  const accessRef = useRef<string | null>(null);
  // Raised just before a deliberate sign-out clears the session, so the pages
  // reacting to that can say "you signed out" instead of "your session expired".
  const signOutIntentRef = useRef(false);

  const applySession = useCallback(
    (nextUser: AuthUser | null, access: string | null) => {
      accessRef.current = access;
      setUser(nextUser);
      setStatus(nextUser ? "authenticated" : "anonymous");
      return nextUser;
    },
    [],
  );

  // Restore the session on first mount.
  useEffect(() => {
    let cancelled = false;

    session
      .current()
      .then((payload) => {
        if (!cancelled) applySession(payload.user, payload.access);
      })
      .catch(() => {
        if (!cancelled) applySession(null, null);
      });

    return () => {
      cancelled = true;
    };
  }, [applySession]);

  // Concurrent callers are collapsed into a single rotation inside `lib/auth`,
  // so this can stay a plain call.
  const refreshAccess = useCallback(async () => {
    try {
      const payload = await session.refresh();
      accessRef.current = payload.access;
      return payload.access;
    } catch {
      applySession(null, null);
      return null;
    }
  }, [applySession]);

  const authFetch = useCallback(
    async <T,>(path: string, options: ApiFetchOptions = {}): Promise<T> => {
      const token = accessRef.current ?? (await refreshAccess());

      try {
        return await apiFetch<T>(path, { ...options, token });
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401) throw error;

        const renewed = await refreshAccess();
        if (!renewed) throw error;
        return apiFetch<T>(path, { ...options, token: renewed });
      }
    },
    [refreshAccess],
  );

  const signIn = useCallback(
    async (email: string, password: string) => {
      const payload = await session.login(email, password);
      const signedIn = applySession(payload.user, payload.access);
      if (!signedIn) throw new Error("Sign in did not return a user.");
      return signedIn;
    },
    [applySession],
  );

  const completeVerification = useCallback(
    async (email: string, code: string) => {
      const payload = await session.verifyOtp(email, code);
      const signedIn = applySession(payload.user, payload.access);
      if (!signedIn) throw new Error("Verification did not return a user.");
      return signedIn;
    },
    [applySession],
  );

  const signOut = useCallback(async () => {
    signOutIntentRef.current = true;
    try {
      await session.logout();
    } finally {
      applySession(null, null);
    }
  }, [applySession]);

  const consumeSignOutIntent = useCallback(() => {
    const intended = signOutIntentRef.current;
    signOutIntentRef.current = false;
    return intended;
  }, []);

  const reloadUser = useCallback(async () => {
    try {
      const fresh = await authFetch<AuthUser>("/auth/me/");
      setUser(fresh);
    } catch {
      applySession(null, null);
    }
  }, [authFetch, applySession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      isAuthenticated: status === "authenticated",
      signIn,
      completeVerification,
      signOut,
      consumeSignOutIntent,
      reloadUser,
      authFetch,
    }),
    [
      user,
      status,
      signIn,
      completeVerification,
      signOut,
      consumeSignOutIntent,
      reloadUser,
      authFetch,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside <AuthProvider>.");
  }
  return context;
}
