import type { Metadata } from "next";
import Link from "next/link";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Container } from "@/components/layout/container";
import { OnboardForm } from "@/components/providers/onboard-form";

export const metadata: Metadata = {
  title: "Onboard to Bimaya",
  description:
    "Send an enquiry to list your insurance policies on Bimaya. Our team reviews every provider before onboarding.",
};

export default function OnboardPage() {
  return (
    <>
      <Navbar />

      <main className="flex-1 bg-surface py-16 sm:py-20">
        <Container className="max-w-xl">
          <div className="mb-8">
            <h1 className="font-display text-3xl font-bold tracking-tight text-ink">
              Onboard to the platform
            </h1>
            <p className="mt-3 text-muted">
              Tell us about your company and we&apos;ll be in touch. Providers
              are onboarded by our team after a quick review.{" "}
              <Link
                href="/for-providers"
                className="font-medium text-brand-600 underline-offset-4 hover:underline"
              >
                Learn more
              </Link>
              .
            </p>
          </div>

          <div className="rounded-2xl border border-line bg-card p-6 shadow-sm sm:p-8">
            <OnboardForm />
          </div>
        </Container>
      </main>

      <Footer />
    </>
  );
}
