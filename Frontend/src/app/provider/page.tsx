import type { Metadata } from "next";
import { ProviderDashboard } from "@/components/provider/provider-dashboard";

export const metadata: Metadata = {
  title: "Provider area",
  description: "Manage your company profile and the plans you list on Bimaya.",
  robots: { index: false, follow: false },
};

export default function ProviderPage() {
  return <ProviderDashboard />;
}
