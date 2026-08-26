"use client";

/**
 * Client-side gate for signed-in pages.
 *
 * This is a UX guard, not a security boundary — the API authorises every
 * request on its own. It keeps signed-out visitors from staring at an empty
 * shell and sends them to sign in with a `next` hop back.
 */
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Container } from "@/components/layout/container";
import { Spinner } from "@/components/ui/spinner";
import type { UserRole } from "@/lib/api";

export function RequireAuth({
  children,
  roles,
}: {
  children: React.ReactNode;
  /** Restrict the page to these roles; others are bounced to the dashboard. */
  roles?: UserRole[];
}) {
  const { status, user, consumeSignOutIntent } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const allowed = !roles || (user ? roles.includes(user.role) : false);
  // Tells "your session ran out while you were here" apart from "you were never
  // signed in", which need different messages on the login page.
  const wasSignedIn = useRef(false);

  useEffect(() => {
    if (status === "loading") return;

    if (status === "authenticated") {
      wasSignedIn.current = true;
      if (!allowed) router.replace("/dashboard");
      return;
    }

    // Signing out from a protected page lands here too. This redirect is the
    // only one, so the sign-out button does not have to race it — it just
    // clears the session and lets the gate move the user.
    if (consumeSignOutIntent()) {
      router.replace("/login?notice=signedout");
      return;
    }

    const query = searchParams.toString();
    const next = encodeURIComponent(query ? `${pathname}?${query}` : pathname);
    router.replace(
      wasSignedIn.current
        ? `/login?notice=expired&next=${next}`
        : `/login?next=${next}`,
    );
  }, [status, allowed, pathname, searchParams, router, consumeSignOutIntent]);

  if (status !== "authenticated" || !allowed) {
    return (
      <Container className="flex flex-1 items-center justify-center py-24">
        <p className="flex items-center gap-2.5 text-sm text-muted">
          <Spinner className="h-4 w-4 text-brand-500" />
          Checking your session…
        </p>
        <span className="sr-only" role="status">
          Loading
        </span>
      </Container>
    );
  }

  return <>{children}</>;
}
