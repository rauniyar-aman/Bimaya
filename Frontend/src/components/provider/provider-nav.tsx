"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { BadgeCheckIcon, BuildingIcon, UsersIcon } from "@/components/icons";

// Each tab names the provider permission that gates its underlying API, so a
// member only sees the sections their org role can actually use. This is
// display only — the backend authorises every request itself. Dashboard has no
// gate: any member of an onboarded organisation can see their own area.
const SECTIONS = [
  { href: "/provider", label: "Dashboard", icon: BuildingIcon, exact: true },
  { href: "/provider/staff", label: "Staff", icon: UsersIcon, permission: "staff.view" },
  { href: "/provider/kyc", label: "KYC", icon: BadgeCheckIcon, permission: "provider_kyc.view" },
];

/**
 * Horizontal section nav for the provider portal. Mirrors {@link AdminNav} but
 * gates on the caller's *organisation* permissions (`profile.my_permissions`),
 * not their staff permissions — a provider member is a `PROVIDER` user whose
 * reach is scoped per company.
 */
export function ProviderNav({ permissions }: { permissions: string[] }) {
  const pathname = usePathname();
  const sections = SECTIONS.filter(
    (section) => !section.permission || permissions.includes(section.permission),
  );

  return (
    <nav
      aria-label="Provider sections"
      className="flex gap-1 overflow-x-auto border-b border-line pb-px"
    >
      {sections.map((section) => {
        const active = section.exact
          ? pathname === section.href
          : pathname.startsWith(section.href);
        const Icon = section.icon;
        return (
          <Link
            key={section.href}
            href={section.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "inline-flex shrink-0 items-center gap-2 border-b-2 px-3.5 py-2.5 text-sm font-medium transition-colors",
              active
                ? "border-brand-500 text-brand-600"
                : "border-transparent text-muted hover:border-line hover:text-ink",
            )}
          >
            <Icon className="h-4 w-4" />
            {section.label}
          </Link>
        );
      })}
    </nav>
  );
}
