/**
 * Small layout pieces shared by the admin detail pages (user and provider): a
 * titled section that falls back to a placeholder when it has no rows, and a
 * label/value pair for the definition-list summaries.
 */

export function Section({
  title,
  hint,
  empty,
  emptyLabel = "Nothing here yet.",
  children,
}: {
  title: string;
  /** Optional right-aligned note, e.g. "Showing the latest 10 of 42." */
  hint?: string;
  empty: boolean;
  emptyLabel?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-lg font-semibold text-ink">{title}</h3>
        {hint && <p className="text-xs text-muted">{hint}</p>}
      </div>
      {empty ? (
        <p className="rounded-2xl border border-dashed border-line bg-surface/50 p-8 text-center text-sm text-muted">
          {emptyLabel}
        </p>
      ) : (
        children
      )}
    </section>
  );
}

export function Detail({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-muted">
        {label}
      </dt>
      <dd className="mt-0.5 text-ink">{children}</dd>
    </div>
  );
}
