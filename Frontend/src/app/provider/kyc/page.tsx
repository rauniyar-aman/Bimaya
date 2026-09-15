import type { Metadata } from "next";
import { ProviderKycDocuments } from "@/components/provider/provider-kyc-documents";

export const metadata: Metadata = {
  title: "KYC documents",
  description: "Upload and track your Bimaya provider verification documents.",
  robots: { index: false, follow: false },
};

export default function ProviderKycPage() {
  // Gating is display-only and lives in the client component (via the portal's
  // `my_permissions`); the layout requires a PROVIDER account and the backend
  // authorises every request.
  return <ProviderKycDocuments />;
}
