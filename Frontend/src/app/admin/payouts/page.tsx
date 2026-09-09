import type { Metadata } from "next";
import { PayoutsTable } from "@/components/admin/payouts-table";

export const metadata: Metadata = {
  title: "Payouts · Admin",
  description:
    "Provider commission payouts — the platform's earnings and the net owed on each issued sale.",
  robots: { index: false, follow: false },
};

export default function AdminPayoutsPage() {
  return <PayoutsTable />;
}
