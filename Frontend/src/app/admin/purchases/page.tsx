import type { Metadata } from "next";
import { PurchaseVerification } from "@/components/admin/purchase-verification";

export const metadata: Metadata = {
  title: "Purchases · Admin",
  description: "Verify payments and forward purchases to providers for issuance.",
  robots: { index: false, follow: false },
};

export default function AdminPurchasesPage() {
  return <PurchaseVerification />;
}
