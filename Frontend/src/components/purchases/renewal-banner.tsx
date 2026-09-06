import Link from "next/link";
import { Alert } from "@/components/ui/alert";
import { daysUntil } from "@/lib/date";
import type { PolicyPurchase } from "@/lib/api";

/** Active policies within this many days of expiry get a renewal nudge. */
const RENEWAL_WINDOW_DAYS = 30;

interface UpcomingRenewal {
  purchase: PolicyPurchase;
  days: number;
}

/** Active purchases whose cover ends within the renewal window, soonest first. */
function upcomingRenewals(purchases: PolicyPurchase[]): UpcomingRenewal[] {
  return purchases
    .filter((purchase) => purchase.status === "ACTIVE")
    .map((purchase) => ({ purchase, days: daysUntil(purchase.end_date) }))
    .filter(
      (item): item is UpcomingRenewal =>
        item.days !== null && item.days >= 0 && item.days <= RENEWAL_WINDOW_DAYS,
    )
    .sort((a, b) => a.days - b.days);
}

/**
 * In-app renewal reminder. Web has no push notifications, so an active policy
 * nearing its end date surfaces here (email reminders are a later slice).
 */
export function RenewalBanner({ purchases }: { purchases: PolicyPurchase[] }) {
  const renewals = upcomingRenewals(purchases);
  if (renewals.length === 0) return null;

  const { purchase, days } = renewals[0];
  const when =
    days === 0 ? "today" : days === 1 ? "tomorrow" : `in ${days} days`;
  const more = renewals.length - 1;

  return (
    <Alert variant="info" className="mb-6">
      <span className="font-medium">{purchase.policy.name}</span> renews {when}.
      Review your cover to stay protected.
      {more > 0 && (
        <>
          {" "}
          {more} other {more === 1 ? "policy" : "policies"} also{" "}
          {more === 1 ? "needs" : "need"} attention soon.
        </>
      )}{" "}
      <Link
        href={`/dashboard/policies/${purchase.id}`}
        className="font-medium underline underline-offset-4"
      >
        View policy
      </Link>
    </Alert>
  );
}
