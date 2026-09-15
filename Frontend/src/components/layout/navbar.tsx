"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Logo } from "@/components/brand/logo";
import { Container } from "@/components/layout/container";
import { UserMenu } from "@/components/layout/user-menu";
import { NotificationBell } from "@/components/notifications/notification-bell";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { accountMenuLinks, homeForRole, primaryNavLinks } from "@/lib/user";

// Highlight the section the user is in. Anchor links to the homepage (e.g.
// "/#how-it-works") never count as a location. A route is active on its own page
// and on any page nested below it, so "Policies" stays lit on a policy detail.
function isActive(pathname: string, href: string): boolean {
  if (href.includes("#")) return false;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Navbar() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const { status, isAuthenticated, user, signOut } = useAuth();

  // The logo takes you "home" — for a signed-in user that is their own area,
  // not the guest marketing page.
  const homeHref = isAuthenticated && user ? homeForRole(user.role) : "/";

  // Marketing/shopping links are for guests and customers. Admins and providers
  // navigate inside their own portals, so their top bar carries no nav links.
  const navLinks = primaryNavLinks(isAuthenticated && user ? user.role : null);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-card/85 backdrop-blur">
      <Container className="flex h-16 items-center justify-between gap-4">
        <Link href={homeHref} aria-label="Bimaya home" className="flex items-center">
          <Logo height={34} priority />
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {navLinks.map((link) => {
            const active = isActive(pathname, link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-brand-50 text-brand-600"
                    : "text-ink/80 hover:bg-surface hover:text-brand-600",
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <ThemeToggle />
          {status === "loading" ? (
            // Reserve the space so the header does not jump once the session
            // has been restored from the refresh cookie.
            <div
              aria-hidden="true"
              className="h-10 w-40 animate-pulse rounded-full bg-surface"
            />
          ) : isAuthenticated ? (
            <>
              <NotificationBell />
              <UserMenu />
            </>
          ) : (
            <>
              <Link href="/login" className={buttonVariants({ variant: "ghost", size: "sm" })}>
                Log in
              </Link>
              <Link href="/register" className={buttonVariants({ variant: "cta", size: "sm" })}>
                Get started
              </Link>
            </>
          )}
        </div>

        <div className="flex items-center gap-1 md:hidden">
          <ThemeToggle />
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label="Toggle menu"
            aria-expanded={open}
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-ink transition-colors hover:bg-surface"
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.8}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              {open ? (
                <>
                  <path d="M18 6 6 18" />
                  <path d="m6 6 12 12" />
                </>
              ) : (
                <>
                  <path d="M4 6h16" />
                  <path d="M4 12h16" />
                  <path d="M4 18h16" />
                </>
              )}
            </svg>
          </button>
        </div>
      </Container>

      {open && (
        <div className="border-t border-line bg-card md:hidden">
          <Container className="flex flex-col gap-1 py-3">
            {navLinks.map((link) => {
              const active = isActive(pathname, link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setOpen(false)}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    active
                      ? "bg-brand-50 text-brand-600"
                      : "text-ink/80 hover:bg-surface hover:text-brand-600",
                  )}
                >
                  {link.label}
                </Link>
              );
            })}
            {isAuthenticated && user ? (
              <div
                className={cn(
                  "space-y-1",
                  navLinks.length > 0 && "mt-2 border-t border-line pt-3",
                )}
              >
                <p className="px-3 pb-1 text-xs text-muted">
                  Signed in as{" "}
                  <span className="font-medium text-ink">{user.email}</span>
                </p>
                {accountMenuLinks(user).map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setOpen(false)}
                    className="block rounded-lg px-3 py-2.5 text-sm font-medium text-ink/80 transition-colors hover:bg-surface hover:text-brand-600"
                  >
                    {link.label}
                  </Link>
                ))}
                <button
                  type="button"
                  onClick={async () => {
                    setOpen(false);
                    await signOut();
                  }}
                  className="block w-full rounded-lg px-3 py-2.5 text-left text-sm font-medium text-danger transition-colors hover:bg-danger-surface"
                >
                  Sign out
                </button>
              </div>
            ) : (
              status !== "loading" && (
                <div className="mt-2 flex gap-2">
                  <Link
                    href="/login"
                    onClick={() => setOpen(false)}
                    className={cn(buttonVariants({ variant: "secondary", size: "md" }), "flex-1")}
                  >
                    Log in
                  </Link>
                  <Link
                    href="/register"
                    onClick={() => setOpen(false)}
                    className={cn(buttonVariants({ variant: "cta", size: "md" }), "flex-1")}
                  >
                    Get started
                  </Link>
                </div>
              )
            )}
          </Container>
        </div>
      )}
    </header>
  );
}
