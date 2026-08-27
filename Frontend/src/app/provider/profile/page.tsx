import type { Metadata } from "next";
import Link from "next/link";
import { ProviderProfileForm } from "@/components/provider/profile-form";
import { Container } from "@/components/layout/container";

export const metadata: Metadata = {
  title: "Company profile",
  description: "Set up or update your provider profile on Bimaya.",
  robots: { index: false, follow: false },
};

export default function ProviderProfilePage() {
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
        <span className="text-ink">Company profile</span>
      </nav>

      <div className="mt-6 max-w-2xl">
        <ProviderProfileForm />
      </div>
    </Container>
  );
}
