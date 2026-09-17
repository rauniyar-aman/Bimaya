import type { Metadata } from "next";
import { ProviderDetail } from "@/components/admin/provider-detail";

type Params = Promise<{ id: string }>;

export const metadata: Metadata = {
  title: "Provider · Admin",
  description: "Full details and history for one insurance provider.",
  robots: { index: false, follow: false },
};

export default async function AdminProviderDetailPage({
  params,
}: {
  params: Params;
}) {
  const { id } = await params;
  return <ProviderDetail id={id} />;
}
