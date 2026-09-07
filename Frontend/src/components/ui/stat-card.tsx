import type { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/cn";

export type StatTone = "brand" | "success" | "accent" | "muted";

const toneClasses: Record<StatTone, string> = {
  brand: "bg-brand-50 text-brand-600",
  success: "bg-success-50 text-success-700",
  accent: "bg-accent-50 text-accent-700",
  muted: "bg-surface text-muted",
};

/**
 * A labelled metric card: a big value, a caption, and an optional icon chip.
 * Built for the admin dashboard now and reused by the analytics panels.
 */
export function StatCard({
  label,
  value,
  hint,
  icon,
  tone = "brand",
  className,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: ReactNode;
  tone?: StatTone;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardContent className="flex items-start justify-between gap-3 p-5">
        <div className="min-w-0">
          <p className="text-sm font-medium text-muted">{label}</p>
          <p className="mt-1 font-display text-2xl font-semibold tracking-tight text-ink">
            {value}
          </p>
          {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
        </div>
        {icon && (
          <span
            className={cn(
              "inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
              toneClasses[tone],
            )}
          >
            {icon}
          </span>
        )}
      </CardContent>
    </Card>
  );
}
