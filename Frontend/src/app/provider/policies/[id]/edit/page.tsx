import type { Metadata } from "next";
import Link from "next/link";
import { PolicyEditor } from "@/components/provider/policy-editor";
import { Container } from "@/components/layout/container";

type Params = Promise<{ id: string }>;

export const metadata: Metadata = {
  title: "Edit policy",
  description: "Update one of your Bimaya insurance plans.",
  robots: { index: false, follow: false },
};

export default async function EditPolicyPage({ params }: { params: Params }) {
  const { id } = await params;

  return (
    <Container className="flex-1 py-10 lg:py-14">
      <nav aria-label="Breadcrumb" className="text-sm text-muted">
        <Link
          href="/provider"
          className="underline-offset-4 transition-colors hover:text-brand-600 hover:underline"
        >
          Provider area
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-ink">Edit policy</span>
      </nav>

      <div className="mt-6 max-w-2xl">
        <PolicyEditor policyId={Number(id)} />
      </div>
    </Container>
  );
}
