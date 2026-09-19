import type { Metadata } from "next";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Container } from "@/components/layout/container";

export const metadata: Metadata = {
  title: "Terms of service",
  description:
    "The terms that govern your use of Bimaya, Nepal's digital insurance marketplace connecting customers with insurance providers.",
};

const LAST_UPDATED = "September 2026";

export default function TermsPage() {
  return (
    <>
      <Navbar />

      <main className="flex-1 bg-surface py-16 sm:py-20">
        <Container className="max-w-3xl">
          <header className="mb-10">
            <h1 className="font-display text-4xl font-bold tracking-tight text-ink">
              Terms of service
            </h1>
            <p className="mt-3 text-sm text-muted">Last updated: {LAST_UPDATED}</p>
            <p className="mt-4 text-muted">
              These terms govern your use of Bimaya. By creating an account or
              using the marketplace, you agree to them. Please read them
              carefully.
            </p>
          </header>

          <div className="space-y-8">
            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                What Bimaya is
              </h2>
              <p className="mt-3 text-muted">
                Bimaya is a marketplace that lets you discover, compare and
                purchase insurance policies offered by third-party insurance
                providers. Bimaya is not an insurer. The insurance contract for
                any policy is between you and the provider that issues it, and
                that provider is responsible for the cover, its terms and any
                claims under it.
              </p>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Your account
              </h2>
              <p className="mt-3 text-muted">
                You must provide accurate information, verify your contact
                details, and keep your login secure. You are responsible for
                activity on your account. You must be old enough to enter into a
                contract under applicable law to buy a policy.
              </p>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Buying a policy
              </h2>
              <p className="mt-3 text-muted">
                To buy a policy you provide nominee details and upload the
                required KYC documents, then pay through a supported gateway
                (eSewa or Khalti). A purchase is confirmed only after payment and
                verification; the provider then issues the policy and a policy
                number is recorded. You are responsible for the accuracy of the
                information you submit.
              </p>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Payments
              </h2>
              <p className="mt-3 text-muted">
                Premiums are shown on each policy and collected through the
                payment gateway you choose. Refunds, cancellations and renewals
                follow the terms of the specific policy and the issuing
                provider&apos;s rules.
              </p>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Claims
              </h2>
              <p className="mt-3 text-muted">
                You can file claims through Bimaya and track their status. Claim
                decisions and settlements are made by the issuing provider
                according to the policy terms. Bimaya facilitates communication
                but does not decide claims.
              </p>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Providers
              </h2>
              <p className="mt-3 text-muted">
                Insurance providers are onboarded and approved by Bimaya before
                they can list policies, and each policy is reviewed before it is
                published. Providers are responsible for the accuracy of their
                policy information and for servicing the policies they issue.
              </p>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Acceptable use
              </h2>
              <p className="mt-3 text-muted">
                Do not misuse the platform — including attempting to access
                accounts that are not yours, disrupting the service, or
                submitting false information. We may suspend accounts that breach
                these terms.
              </p>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Changes to these terms
              </h2>
              <p className="mt-3 text-muted">
                We may update these terms as the platform evolves. When we make
                material changes we will update the date above and, where
                appropriate, notify you. Continued use of Bimaya means you accept
                the updated terms.
              </p>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Contact
              </h2>
              <p className="mt-3 text-muted">
                Questions about these terms? Email{" "}
                <a
                  href="mailto:support@bimaya.com"
                  className="font-medium text-brand-ink underline-offset-4 hover:underline"
                >
                  support@bimaya.com
                </a>
                .
              </p>
            </section>
          </div>
        </Container>
      </main>

      <Footer />
    </>
  );
}
