import type { Metadata } from "next";
import { RequireAuth } from "@/components/auth/require-auth";
import { RolesMatrix } from "@/components/admin/roles-matrix";

export const metadata: Metadata = {
  title: "Roles · Admin",
  description: "The read-only staff roles and permissions matrix.",
  robots: { index: false, follow: false },
};

export default function AdminRolesPage() {
  return (
    <RequireAuth permission="role.view">
      <RolesMatrix />
    </RequireAuth>
  );
}
