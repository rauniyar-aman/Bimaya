import { Button } from "@/components/ui/button";

/**
 * Previous / Next pager for the DRF page-number lists. `count` is the total row
 * count and `pageSize` the server page size (12), so the control can show
 * "Page X of Y" and disable the ends.
 */
export function Pagination({
  page,
  count,
  pageSize = 12,
  onChange,
  disabled = false,
}: {
  page: number;
  count: number;
  pageSize?: number;
  onChange: (page: number) => void;
  disabled?: boolean;
}) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-center gap-3">
      <Button
        variant="secondary"
        size="sm"
        onClick={() => onChange(Math.max(1, page - 1))}
        disabled={disabled || page <= 1}
      >
        Previous
      </Button>
      <span className="text-sm text-muted">
        Page {page} of {totalPages}
      </span>
      <Button
        variant="secondary"
        size="sm"
        onClick={() => onChange(Math.min(totalPages, page + 1))}
        disabled={disabled || page >= totalPages}
      >
        Next
      </Button>
    </div>
  );
}
