import type { Metadata } from "next";
import { UserDetail } from "@/components/admin/user-detail";

type Params = Promise<{ id: string }>;

export const metadata: Metadata = {
  title: "User · Admin",
  description: "Full details and history for one Bimaya account.",
  robots: { index: false, follow: false },
};

export default async function AdminUserDetailPage({
  params,
}: {
  params: Params;
}) {
  const { id } = await params;
  return <UserDetail id={id} />;
}
