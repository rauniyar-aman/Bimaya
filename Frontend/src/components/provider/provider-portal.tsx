"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { ProviderNav } from "@/components/provider/provider-nav";
import { Container } from "@/components/layout/container";
import { Alert } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { api, errorCode, type ProviderProfile } from "@/lib/api";

interface ProviderPortalValue {
  /** The signed-in user's organisation, or `null` before it is set up. */
  profile: ProviderProfile | null;
  /** The `module.action` permissions the user holds here. Display-only. */
  permissions: string[];
  /** Re-fetch the profile (call after creating/editing it, or changing roles). */
  refresh: () => void;
}

const ProviderPortalContext = createContext<ProviderPortalValue | null>(null);

/**
 * Read the shared provider-portal state. Must be used under {@link ProviderPortal}
 * (the provider layout wraps every `/provider` page in it).
 */
export function useProviderPortal(): ProviderPortalValue {
  const ctx = useContext(ProviderPortalContext);
  if (!ctx) {
    throw new Error("useProviderPortal must be used within <ProviderPortal>");
  }
  return ctx;
}

type LoadState =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; profile: ProviderProfile | null };

/**
 * The provider portal shell: loads the organisation profile once, shares it (and
 * the caller's org permissions) with every page via context, and renders the
 * section nav. A missing profile is the first-run *setup* state, not an error —
 * a fresh owner lands on the dashboard's "set up your profile" card. The nav only
 * appears once the organisation exists.
 */
export function ProviderPortal({ children }: { children: React.ReactNode }) {
  const { authFetch } = useAuth();
  const [state, setState] = useState<LoadState>({ phase: "loading" });
  // Bumped by refresh() so the profile refetches after a create/edit/role change.
  const [reloadKey, setReloadKey] = useState(0);

  const refresh = useCallback(() => setReloadKey((k) => k + 1), []);

  useEffect(() => {
    let cancelled = false;
    api.provider
      .getProfile(authFetch)
      .then((profile) => {
        if (!cancelled) setState({ phase: "ready", profile });
      })
      .catch((error) => {
        if (cancelled) return;
        // No organisation yet is the expected first-run case, not an error.
        if (errorCode(error) === "provider_profile_missing")
          setState({ phase: "ready", profile: null });
        else setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, reloadKey]);

  if (state.phase === "loading") {
    return (
      <Container className="flex flex-1 items-center justify-center py-24">
        <Spinner className="h-6 w-6 text-brand-500" />
      </Container>
    );
  }

  if (state.phase === "error") {
    return (
      <Container className="flex-1 py-10">
        <Alert variant="error">
          We could not load your provider area. Please refresh and try again.
        </Alert>
      </Container>
    );
  }

  const { profile } = state;
  const permissions = profile?.my_permissions ?? [];

  return (
    <ProviderPortalContext.Provider value={{ profile, permissions, refresh }}>
      <Container className="flex-1 py-8 lg:py-10">
        {profile && <ProviderNav permissions={permissions} />}
        <div className={profile ? "mt-8" : ""}>{children}</div>
      </Container>
    </ProviderPortalContext.Provider>
  );
}
