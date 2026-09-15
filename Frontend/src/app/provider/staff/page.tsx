import type { Metadata } from "next";
import { ProviderStaffTable } from "@/components/provider/provider-staff-table";

export const metadata: Metadata = {
  title: "Team",
  description: "Manage your Bimaya provider team and the access each member has.",
  robots: { index: false, follow: false },
};

export default function ProviderStaffPage() {
  // Gating is display-only and lives in the client component (via the portal's
  // `my_permissions`); the provider layout already requires a PROVIDER account,
  // and the backend authorises every request.
  return <ProviderStaffTable />;
}
