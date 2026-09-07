"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import {
  BuildingIcon,
  ChartIcon,
  ClipboardIcon,
  FileTextIcon,
  BadgeCheckIcon,
  UsersIcon,
} from "@/components/icons";

const SECTIONS = [
  { href: "/admin", label: "Overview", icon: ChartIcon, exact: true },
  { href: "/admin/providers", label: "Providers", icon: BuildingIcon },
  { href: "/admin/kyc", label: "KYC review", icon: BadgeCheckIcon },
  { href: "/admin/purchases", label: "Purchases", icon: ClipboardIcon },
  { href: "/admin/users", label: "Users", icon: UsersIcon },
  { href: "/admin/policies", label: "Policies", icon: FileTextIcon },
];

/** Horizontal, scrollable section nav for the admin area. */
export function AdminNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Admin sections"
      className="flex gap-1 overflow-x-auto border-b border-line pb-px"
    >
      {SECTIONS.map((section) => {
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
