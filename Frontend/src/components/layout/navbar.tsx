"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Logo } from "@/components/brand/logo";
import { Container } from "@/components/layout/container";
import { UserMenu } from "@/components/layout/user-menu";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";

const NAV_LINKS = [
  { href: "/policies", label: "Policies" },
  { href: "/compare", label: "Compare" },
  { href: "/categories", label: "Categories" },
  { href: "/#how-it-works", label: "How it works" },
];

export function Navbar() {
  const [open, setOpen] = useState(false);
  const { status, isAuthenticated, user, signOut } = useAuth();

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-white/85 backdrop-blur">
      <Container className="flex h-16 items-center justify-between gap-4">
        <Link href="/" aria-label="Bimaya home" className="flex items-center">
          <Logo height={34} priority />
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-ink/80 transition-colors hover:bg-surface hover:text-brand-600"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          {status === "loading" ? (
            // Reserve the space so the header does not jump once the session
            // has been restored from the refresh cookie.
            <div
              aria-hidden="true"
              className="h-10 w-40 animate-pulse rounded-full bg-surface"
            />
          ) : isAuthenticated ? (
            <UserMenu />
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

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label="Toggle menu"
          aria-expanded={open}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-ink transition-colors hover:bg-surface md:hidden"
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
      </Container>

      {open && (
        <div className="border-t border-line bg-white md:hidden">
          <Container className="flex flex-col gap-1 py-3">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-2.5 text-sm font-medium text-ink/80 transition-colors hover:bg-surface hover:text-brand-600"
              >
                {link.label}
              </Link>
            ))}
            {isAuthenticated && user ? (
              <div className="mt-2 space-y-1 border-t border-line pt-3">
                <p className="px-3 pb-1 text-xs text-muted">
                  Signed in as{" "}
                  <span className="font-medium text-ink">{user.email}</span>
                </p>
                <Link
                  href="/dashboard"
                  onClick={() => setOpen(false)}
                  className="block rounded-lg px-3 py-2.5 text-sm font-medium text-ink/80 transition-colors hover:bg-surface hover:text-brand-600"
                >
                  Dashboard
                </Link>
                <button
                  type="button"
                  onClick={async () => {
                    setOpen(false);
                    await signOut();
                  }}
                  className="block w-full rounded-lg px-3 py-2.5 text-left text-sm font-medium text-red-600 transition-colors hover:bg-red-50"
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
