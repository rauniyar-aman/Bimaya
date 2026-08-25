import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export type StatusVariant =
  | "active"
  | "success"
  | "pending"
  | "failed"
  | "expired"
  | "info";

const styles: Record<StatusVariant, { wrap: string; dot: string }> = {
  active: {
    wrap: "border-success-500 bg-success-50 text-success-700",
    dot: "bg-success-500",
  },
  success: {
    wrap: "border-success-500 bg-success-50 text-success-700",
    dot: "bg-success-500",
  },
  pending: {
    wrap: "border-accent-300 bg-accent-50 text-accent-700",
    dot: "bg-accent-500",
  },
  failed: {
    wrap: "border-red-200 bg-red-50 text-red-600",
    dot: "bg-red-500",
  },
  expired: {
    wrap: "border-slate-200 bg-slate-100 text-slate-600",
    dot: "bg-slate-400",
  },
  info: {
    wrap: "border-brand-200 bg-brand-50 text-brand-700",
    dot: "bg-brand-500",
  },
};

interface StatusPillProps {
  status?: StatusVariant;
  children: ReactNode;
  className?: string;
}

export function StatusPill({
  status = "info",
  children,
  className,
}: StatusPillProps) {
  const s = styles[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        s.wrap,
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", s.dot)} />
      {children}
    </span>
  );
}
