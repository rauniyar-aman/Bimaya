"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth/auth-provider";
import { Container } from "@/components/layout/container";
import { Logo } from "@/components/brand/logo";
import { BackendStatus } from "@/components/site/backend-status";
import { isPortalRole } from "@/lib/user";

const COLUMNS: { title: string; links: { href: string; label: string }[] }[] = [
  {
    title: "Product",
    links: [
      { href: "/policies", label: "Browse policies" },
      { href: "/compare", label: "Compare plans" },
      { href: "/categories", label: "Categories" },
    ],
  },
  {
    title: "Company",
    links: [
      { href: "/about", label: "About Bimaya" },
      { href: "/#how-it-works", label: "How it works" },
      { href: "/for-providers", label: "For insurance providers" },
      { href: "/contact", label: "Contact" },
    ],
  },
  {
    title: "Legal",
    links: [
      { href: "/privacy", label: "Privacy policy" },
      { href: "/terms", label: "Terms of service" },
    ],
  },
];

export function Footer() {
  const { isAuthenticated, user } = useAuth();
  // Admins and providers work inside their own portals, so they get a lean
  // footer — brand plus the legal links that apply to everyone — instead of the
  // marketplace and marketing columns aimed at shoppers.
  const lean = isPortalRole(isAuthenticated && user ? user.role : null);

  return (
    <footer className="mt-auto border-t border-line bg-surface">
      <Container className="py-12">
        {lean ? (
          <div className="mx-auto max-w-5xl">
            <Logo height={38} />
          </div>
        ) : (
          <div className="mx-auto grid max-w-5xl gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
            <div className="max-w-xs">
              <Logo height={38} />
              <p className="mt-4 text-sm leading-relaxed text-muted">
                Nepal&apos;s digital insurance marketplace. Compare, buy and manage
                your insurance online — simple, transparent and secure.
              </p>
            </div>

            {COLUMNS.map((col) => (
              <div key={col.title}>
                <h3 className="font-display text-sm font-semibold text-ink">
                  {col.title}
                </h3>
                <ul className="mt-4 space-y-2.5">
                  {col.links.map((link) => (
                    <li key={link.href}>
                      <Link
                        href={link.href}
                        className="text-sm text-muted transition-colors hover:text-brand-ink"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        <div className="mx-auto mt-10 flex max-w-5xl flex-col items-start justify-between gap-4 border-t border-line pt-6 sm:flex-row sm:items-center">
          <p className="text-xs text-muted">
            © 2026 Bimaya. Insurance products are offered by licensed providers.
          </p>
          <div className="flex items-center gap-5">
            {lean && (
              <nav aria-label="Legal" className="flex items-center gap-5">
                <Link
                  href="/privacy"
                  className="text-xs text-muted transition-colors hover:text-brand-ink"
                >
                  Privacy
                </Link>
                <Link
                  href="/terms"
                  className="text-xs text-muted transition-colors hover:text-brand-ink"
                >
                  Terms
                </Link>
              </nav>
            )}
            <BackendStatus />
          </div>
        </div>
      </Container>
    </footer>
  );
}
