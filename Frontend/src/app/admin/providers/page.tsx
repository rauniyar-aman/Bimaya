import type { Metadata } from "next";
import { ProviderApprovals } from "@/components/admin/provider-approvals";

export const metadata: Metadata = {
  title: "Providers · Admin",
  description: "Approve and manage insurance providers on Bimaya.",
  robots: { index: false, follow: false },
};

export default function AdminProvidersPage() {
  return <ProviderApprovals />;
}
