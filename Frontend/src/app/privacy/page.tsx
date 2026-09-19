import type { Metadata } from "next";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Container } from "@/components/layout/container";

export const metadata: Metadata = {
  title: "Privacy policy",
  description:
    "How Bimaya collects, uses and protects your personal information, KYC documents and payment details on Nepal's digital insurance marketplace.",
};

const LAST_UPDATED = "September 2026";

export default function PrivacyPage() {
  return (
    <>
      <Navbar />

      <main className="flex-1 bg-surface py-16 sm:py-20">
        <Container className="max-w-3xl">
          <header className="mb-10">
            <h1 className="font-display text-4xl font-bold tracking-tight text-ink">
              Privacy policy
            </h1>
            <p className="mt-3 text-sm text-muted">Last updated: {LAST_UPDATED}</p>
            <p className="mt-4 text-muted">
              This policy explains what information Bimaya collects when you use
              our marketplace, how we use it, and the choices you have. By using
              Bimaya you agree to the practices described here.
            </p>
          </header>

          <div className="space-y-8">
            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Information we collect
              </h2>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-muted">
                <li>
                  <span className="font-medium text-ink">Account details</span>{" "}
                  — your name, email and phone number, used to create and secure
                  your account and to verify you with a one-time code.
                </li>
                <li>
                  <span className="font-medium text-ink">KYC documents</span> —
                  identity and related documents you upload to purchase a policy,
                  used only to verify you and issue your cover.
                </li>
                <li>
                  <span className="font-medium text-ink">Policy and claim data</span>{" "}
                  — the policies you buy, nominee details you provide and claims
                  you file, used to manage your cover.
                </li>
                <li>
                  <span className="font-medium text-ink">Payment information</span>{" "}
                  — payments are processed by eSewa and Khalti. We record the
                  outcome of a transaction, not your full payment credentials.
                </li>
              </ul>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                How we use your information
              </h2>
              <p className="mt-3 text-muted">
                We use your information to run the marketplace: to verify your
                identity, process purchases and payments, issue and manage
                policies, handle claims, send you service notifications such as
                renewal reminders, and keep the platform secure. We do not sell
                your personal information.
              </p>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Sharing with insurance providers
              </h2>
              <p className="mt-3 text-muted">
                When you buy a policy or file a claim, the relevant details are
                shared with the insurance provider issuing that policy so they
                can service it. Providers only see the information needed for the
                policies and claims that involve them.
              </p>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Automated assistance
              </h2>
              <p className="mt-3 text-muted">
                Bimaya offers tools that help you find suitable policies and
                answer general insurance questions. These tools work from public
                catalogue information and the questions you choose to ask. Please
                do not enter identity numbers, health details or other sensitive
                personal information into the chat assistant.
              </p>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Data security
              </h2>
              <p className="mt-3 text-muted">
                We protect your information with encryption in transit, secure
                password storage and role-based access controls, so that only the
                people who need your information can see it. No system is
                perfectly secure, but we work to safeguard your data and to
                comply with applicable regulations.
              </p>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Your choices
              </h2>
              <p className="mt-3 text-muted">
                You can view and update your account details and manage your
                policies from your dashboard. If you would like a copy of your
                data or want to close your account, contact us and we will help.
              </p>
            </section>

            <section>
              <h2 className="font-display text-2xl font-semibold text-ink">
                Contact
              </h2>
              <p className="mt-3 text-muted">
                Questions about this policy or your data? Email{" "}
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
