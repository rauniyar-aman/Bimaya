import type { Metadata } from "next";
import { RequireAuth } from "@/components/auth/require-auth";
import { AuditLog } from "@/components/admin/audit-log";

export const metadata: Metadata = {
  title: "Audit log · Admin",
  description: "An append-only record of administrative actions on Bimaya.",
  robots: { index: false, follow: false },
};

export default function AdminAuditPage() {
  return (
    <RequireAuth permission="audit_log.view">
      <AuditLog />
    </RequireAuth>
  );
}
