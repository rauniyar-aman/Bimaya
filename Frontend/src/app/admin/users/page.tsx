import type { Metadata } from "next";
import { UsersTable } from "@/components/admin/users-table";

export const metadata: Metadata = {
  title: "Users · Admin",
  description: "Browse customers, providers, and admins on Bimaya.",
  robots: { index: false, follow: false },
};

export default function AdminUsersPage() {
  return <UsersTable />;
}
