import type { Metadata } from "next";
import { RequireAuth } from "@/components/auth/require-auth";
import { StaffTable } from "@/components/admin/staff-table";

export const metadata: Metadata = {
  title: "Staff · Admin",
  description: "Manage internal-staff accounts and their roles on Bimaya.",
  robots: { index: false, follow: false },
};

export default function AdminStaffPage() {
  return (
    <RequireAuth permission="staff.view">
      <StaffTable />
    </RequireAuth>
  );
}
