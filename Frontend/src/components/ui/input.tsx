import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

/**
 * Shared visual styling for text-like controls, without horizontal padding so
 * composed inputs can set their own. Plain `Input` applies `px-3.5`;
 * `PasswordInput` uses `pl-3.5 pr-11` to leave room for its show/hide toggle.
 * (`cn` is a plain join with no Tailwind conflict resolution, so the padding
 * has to be kept out of the base rather than overridden per caller.)
 */
export const inputBase =
  "h-11 w-full rounded-lg border border-line bg-card text-sm text-ink transition-colors placeholder:text-muted/70 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100 disabled:cursor-not-allowed disabled:opacity-60";

export function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(inputBase, "px-3.5", className)} {...props} />;
}
