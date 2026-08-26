import Link from "next/link";
import type { ReactNode } from "react";

/** Title block at the top of every auth screen. */
export function AuthHeading({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="mb-7 space-y-2">
      <h1 className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-[1.75rem]">
        {title}
      </h1>
      {children && (
        <p className="text-sm leading-relaxed text-muted">{children}</p>
      )}
    </div>
  );
}

/** "Already have an account?" style line under the form. */
export function AuthFootnote({
  prompt,
  href,
  action,
}: {
  prompt: string;
  href: string;
  action: string;
}) {
  return (
    <p className="mt-6 text-center text-sm text-muted">
      {prompt}{" "}
      <Link
        href={href}
        className="font-medium text-brand-600 underline-offset-4 hover:underline"
      >
        {action}
      </Link>
    </p>
  );
}
