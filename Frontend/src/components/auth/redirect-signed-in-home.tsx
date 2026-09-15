"use client";

/**
 * The homepage is the marketing splash for signed-out visitors. A signed-in
 * user who lands on it — via the logo, a bookmark or a returning visit — is
 * sent on to their own home (customer dashboard, provider area or admin panel)
 * instead of the guest page.
 *
 * Renders nothing for guests, and while the session is still being restored, so
 * the marketing page paints immediately and stays crawlable. Once the user is
 * known to be signed in it covers the page with a spinner while the redirect
 * runs, so they never appear stuck on the guest splash.
 */
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Spinner } from "@/components/ui/spinner";
import { homeForRole } from "@/lib/user";

export function RedirectSignedInHome() {
  const { status, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated" && user) {
      router.replace(homeForRole(user.role));
    }
  }, [status, user, router]);

  if (status !== "authenticated") return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-background">
      <Spinner className="h-5 w-5 text-brand-500" />
      <span className="sr-only" role="status">
        Taking you to your account…
      </span>
    </div>
  );
}
