import type { Metadata } from "next";
import Link from "next/link";
import { KycManager } from "@/components/kyc/kyc-manager";
import { Container } from "@/components/layout/container";

export const metadata: Metadata = {
  title: "KYC verification",
  description: "Submit and manage your Bimaya identity verification.",
  robots: { index: false, follow: false },
};

export default function KycPage() {
  return (
    <Container className="flex-1 py-10 lg:py-14">
      <nav aria-label="Breadcrumb" className="text-sm text-muted">
        <Link
          href="/dashboard"
          className="underline-offset-4 transition-colors hover:text-brand-ink hover:underline"
        >
          Dashboard
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-ink">KYC verification</span>
      </nav>

      <h1 className="mt-3 font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
        KYC verification
      </h1>
      <p className="mt-1.5 max-w-2xl text-sm text-muted">
        Complete your Know-Your-Customer details once. We reuse your verified KYC
        for your own future purchases, so checkout stays quick.
      </p>

      <KycManager />
    </Container>
  );
}
