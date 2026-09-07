import type { Metadata } from "next";
import { PoliciesTable } from "@/components/admin/policies-table";

export const metadata: Metadata = {
  title: "Policies · Admin",
  description: "Every policy listed across providers on Bimaya.",
  robots: { index: false, follow: false },
};

export default function AdminPoliciesPage() {
  return <PoliciesTable />;
}
