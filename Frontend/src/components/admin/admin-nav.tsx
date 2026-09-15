"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { cn } from "@/lib/cn";
import {
  BuildingIcon,
  ChartIcon,
  ClipboardIcon,
  FileTextIcon,
  BadgeCheckIcon,
  HistoryIcon,
  LockIcon,
  ShieldCheckIcon,
  UsersIcon,
  WalletIcon,
} from "@/components/icons";

// Each section names the granular permission that gates its underlying API, so
// a staff member only sees tabs their role can actually use. This is display
// only — the backend authorises every request itself.
const SECTIONS = [
  { href: "/admin", label: "Overview", icon: ChartIcon, exact: true, permission: "dashboard.view" },
  { href: "/admin/providers", label: "Providers", icon: BuildingIcon, permission: "provider.view" },
  { href: "/admin/kyc", label: "KYC review", icon: BadgeCheckIcon, permission: "kyc.view" },
  { href: "/admin/purchases", label: "Purchases", icon: ClipboardIcon, permission: "purchase.view" },
  { href: "/admin/payouts", label: "Payouts", icon: WalletIcon, permission: "settlement.view" },
  { href: "/admin/users", label: "Users", icon: UsersIcon, permission: "customer.view" },
  { href: "/admin/policies", label: "Policies", icon: FileTextIcon, permission: "policy.view" },
  { href: "/admin/staff", label: "Staff", icon: ShieldCheckIcon, permission: "staff.view" },
  { href: "/admin/roles", label: "Roles", icon: LockIcon, permission: "role.view" },
  { href: "/admin/audit", label: "Audit log", icon: HistoryIcon, permission: "audit_log.view" },
];

/**
 * Section nav for the admin area. A vertical sidebar on desktop; on narrow
 * screens it collapses to a horizontally scrollable row of the same pills so
 * every section stays reachable without a menu toggle.
 */
export function AdminNav() {
  const pathname = usePathname();
  const { user } = useAuth();
  const permissions = user?.permissions ?? [];
  const sections = SECTIONS.filter(
    (section) => !section.permission || permissions.includes(section.permission),
  );

  return (
    <nav
      aria-label="Admin sections"
      className="flex gap-1 overflow-x-auto pb-1 lg:flex-col lg:gap-0.5 lg:overflow-visible lg:pb-0"
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
              "inline-flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors lg:w-full",
              active
                ? "bg-brand-50 text-brand-600"
                : "text-muted hover:bg-surface hover:text-ink",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {section.label}
          </Link>
        );
      })}
    </nav>
  );
}
