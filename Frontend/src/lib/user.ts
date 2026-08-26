import type { AuthUser, UserRole } from "./api";

export const ROLE_LABELS: Record<UserRole, string> = {
  CUSTOMER: "Customer",
  PROVIDER: "Insurance provider",
  ADMIN: "Administrator",
};

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
