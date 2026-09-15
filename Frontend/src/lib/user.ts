import type { AuthUser, UserRole } from "./api";

export const ROLE_LABELS: Record<UserRole, string> = {
  CUSTOMER: "Customer",
  PROVIDER: "Insurance provider",
  ADMIN: "Administrator",
};

/**
 * The home each role lands on after signing in — their own area, not the
 * customer dashboard. Shared by the auth flow and the dashboard guard so a
 * signed-in admin or provider never lands on the empty customer view.
 */
export function homeForRole(role: UserRole): string {
  if (role === "ADMIN") return "/admin";
  if (role === "PROVIDER") return "/provider";
  return "/dashboard";
}

export interface AccountMenuLink {
  href: string;
  label: string;
}

/**
 * Links shown in the account menu — the header dropdown and the mobile nav —
 * scoped to the user's role. Each role sees only destinations that belong to
 * it: a customer's own policies and claims, a provider's company area, an
 * admin's panel. No role is shown another role's pages. Sign-out is rendered
 * separately by the menu itself, so it is not listed here.
 */
export function accountMenuLinks(user: AuthUser): AccountMenuLink[] {
  if (user.role === "ADMIN") {
    return [{ href: "/admin", label: "Admin panel" }];
  }
  if (user.role === "PROVIDER") {
    return [
      { href: "/provider", label: "Provider area" },
      { href: "/provider/profile", label: "Company profile" },
    ];
  }
  return [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/dashboard/policies", label: "My policies" },
    { href: "/dashboard/claims", label: "My claims" },
    { href: "/dashboard/notifications", label: "Notifications" },
    { href: "/dashboard/kyc", label: "KYC verification" },
    { href: "/dashboard/profile", label: "Profile settings" },
  ];
}

export interface NavLink {
  href: string;
  label: string;
}

/**
 * Whether a role lives inside its own dedicated portal — the admin panel or the
 * provider area, each with its own navigation. Portal roles get lean app chrome
 * (no marketing nav, a stripped-back footer) because the marketplace links are
 * noise to them. Guests and customers (`null` or CUSTOMER) get the full
 * marketing chrome.
 */
export function isPortalRole(role: UserRole | null): boolean {
  return role === "ADMIN" || role === "PROVIDER";
}

/**
 * The marketing and shopping links in the top navigation — browse, compare,
 * get advice, buy. These are the customer journey, so guests and customers see
 * them. Portal roles (admin, provider) navigate inside their own areas, so they
 * get a clean app bar instead: logo, notifications and account menu. Pass
 * `null` for signed-out visitors.
 */
export function primaryNavLinks(role: UserRole | null): NavLink[] {
  if (isPortalRole(role)) return [];
  return [
    { href: "/policies", label: "Policies" },
    { href: "/compare", label: "Compare" },
    { href: "/categories", label: "Categories" },
    { href: "/assistant", label: "AI advisor" },
    { href: "/#how-it-works", label: "How it works" },
  ];
}

/** Name to greet the user by, falling back to the local part of their email. */
export function displayName(user: AuthUser): string {
  const name = user.full_name?.trim();
  if (name) return name;
  return user.email.split("@")[0];
}

export function firstName(user: AuthUser): string {
  return displayName(user).split(/\s+/)[0];
}

/** Up to two initials for the avatar bubble. */
export function initials(user: AuthUser): string {
  const parts = displayName(user).split(/\s+/).filter(Boolean);
  const letters = parts.slice(0, 2).map((part) => part[0]);
  return letters.join("").toUpperCase() || "B";
}
