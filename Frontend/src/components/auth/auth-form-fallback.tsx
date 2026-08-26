/**
 * Placeholder shown while an auth form loads.
 *
 * The forms read `useSearchParams()` to carry the email between steps, so they
 * need a Suspense boundary; this keeps the layout from jumping when it resolves.
 */
export function AuthFormFallback({ fields = 2 }: { fields?: number }) {
  return (
    <div aria-hidden="true" className="animate-pulse space-y-6">
      <div className="space-y-2">
        <div className="h-7 w-3/5 rounded bg-surface" />
        <div className="h-4 w-4/5 rounded bg-surface" />
      </div>
      <div className="space-y-4">
        {Array.from({ length: fields }, (_, index) => (
          <div key={index} className="space-y-1.5">
            <div className="h-4 w-28 rounded bg-surface" />
            <div className="h-11 w-full rounded-lg bg-surface" />
          </div>
        ))}
        <div className="h-12 w-full rounded-lg bg-surface" />
      </div>
    </div>
  );
}
