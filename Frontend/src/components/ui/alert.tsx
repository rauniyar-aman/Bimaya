import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export type AlertVariant = "error" | "success" | "info";

const variantClasses: Record<AlertVariant, string> = {
  error: "border-red-200 bg-red-50 text-red-800",
  success: "border-success-200 bg-success-50 text-success-800",
  info: "border-brand-100 bg-brand-50 text-brand-800",
};

interface AlertProps {
  variant?: AlertVariant;
  className?: string;
  children: ReactNode;
}

export function Alert({ variant = "info", className, children }: AlertProps) {
  return (
    <div
      role={variant === "error" ? "alert" : "status"}
      className={cn(
        "rounded-xl border px-4 py-3 text-sm",
        variantClasses[variant],
        className,
      )}
    >
      {children}
    </div>
  );
}
