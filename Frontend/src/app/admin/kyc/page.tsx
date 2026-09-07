import type { Metadata } from "next";
import { KycReview } from "@/components/admin/kyc-review";

export const metadata: Metadata = {
  title: "KYC review · Admin",
  description: "Review, verify, and reject customer KYC submissions.",
  robots: { index: false, follow: false },
};

export default function AdminKycPage() {
  return <KycReview />;
}
