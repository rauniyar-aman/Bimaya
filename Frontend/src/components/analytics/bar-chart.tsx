import { cn } from "@/lib/cn";

/**
 * Hand-rolled, dependency-free charts for the analytics panels — plain divs
 * scaled against the series maximum, styled with the design tokens. Two shapes:
 * a horizontal {@link BarChart} for categorical breakdowns (status counts, users
 * by role) and a vertical {@link ColumnChart} for the monthly trend. Both take
 * an `ariaLabel` and expose per-bar `title`s so the data is legible without a
 * pointer.
 */

export type ChartTone = "brand" | "accent" | "success";

const fillClasses: Record<ChartTone, string> = {
  brand: "bg-brand-500",
  accent: "bg-accent-500",
  success: "bg-success-500",
};

export interface BarDatum {
  key: string;
  label: string;
  value: number;
  /** What to print at the end of the bar; defaults to `value`. */
  display?: string;
}

/** A horizontal bar per row: label, a proportional track, and the value. */
export function BarChart({
  data,
  tone = "brand",
  ariaLabel,
  emptyLabel = "No data yet.",
}: {
  data: BarDatum[];
  tone?: ChartTone;
  ariaLabel: string;
  emptyLabel?: string;
}) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  if (total === 0) {
    return <p className="py-6 text-center text-sm text-muted">{emptyLabel}</p>;
  }
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="space-y-2.5" role="img" aria-label={ariaLabel}>
      {data.map((d) => {
        const pct = d.value === 0 ? 0 : Math.max(Math.round((d.value / max) * 100), 3);
        return (
          <div
            key={d.key}
            className="grid grid-cols-[7rem_1fr_2.5rem] items-center gap-3 text-sm"
            title={`${d.label}: ${d.display ?? d.value}`}
          >
            <span className="truncate text-muted">{d.label}</span>
            <span className="h-2.5 rounded-full bg-surface">
              <span
                className={cn("block h-full rounded-full", fillClasses[tone])}
                style={{ width: `${pct}%` }}
              />
            </span>
            <span className="text-right font-medium tabular-nums text-ink">
              {d.display ?? d.value}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export interface ColumnDatum {
  label: string;
  value: number;
  /** Printed above the column; defaults to `value`. */
  valueLabel?: string;
  /** A small second line under the label (e.g. premium collected). */
  caption?: string;
}

/** A vertical column per period, scaled to the tallest value in the series. */
export function ColumnChart({
  data,
  tone = "brand",
  ariaLabel,
}: {
  data: ColumnDatum[];
  tone?: ChartTone;
  ariaLabel: string;
}) {
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div role="img" aria-label={ariaLabel}>
      <div className="flex h-40 items-end gap-2">
        {data.map((d) => {
          const pct = d.value === 0 ? 0 : Math.max(Math.round((d.value / max) * 100), 4);
          return (
            <div
              key={d.label}
              className="flex h-full flex-1 flex-col justify-end"
              title={`${d.label}: ${d.valueLabel ?? d.value}${d.caption ? ` · ${d.caption}` : ""}`}
            >
              <span className="mb-1 text-center text-[11px] font-medium tabular-nums text-ink">
                {d.valueLabel ?? d.value}
              </span>
              <div
                className={cn("w-full rounded-t-md", fillClasses[tone])}
                style={{ height: `${pct}%` }}
              />
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex gap-2">
        {data.map((d) => (
          <div key={d.label} className="flex-1 text-center">
            <div className="text-xs text-muted">{d.label}</div>
            {d.caption && (
              <div className="truncate text-[10px] text-muted" title={d.caption}>
                {d.caption}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
