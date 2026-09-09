import type { Metadata } from "next";
import Link from "next/link";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Container } from "@/components/layout/container";

export const metadata: Metadata = {
  title: "About Bimaya",
  description:
    "Bimaya is Nepal's digital insurance marketplace — compare, buy and manage Life, Health, Vehicle and Travel insurance online, across multiple providers, in one trusted place.",
};

const AUDIENCE = [
  {
    title: "For customers",
    body: "Compare policies from multiple insurers side by side, buy online with eSewa or Khalti, and manage everything — purchases, documents and claims — from one dashboard.",
  },
  {
    title: "For providers",
    body: "Insurance companies reach new customers through a single digital channel: publish a policy catalogue, track sales and handle claims, without building their own platform.",
  },
  {
    title: "For trust",
    body: "Every provider and every policy is reviewed by a Bimaya administrator before it reaches customers, so the marketplace stays credible and safe.",
  },
];

const STEPS = [
  "Register and verify your phone or email with a one-time code.",
  "Discover and compare policies by category — Life, Health, Vehicle and Travel.",
  "Choose a policy, add nominee details and upload your KYC documents.",
  "Pay securely online through eSewa or Khalti.",
  "Your policy is issued after verification, with a policy number and digital receipt.",
  "Manage your cover, get renewal reminders and file claims — all online.",
];

export default function AboutPage() {
  return (
    <>
      <Navbar />

      <main className="flex-1 bg-surface py-16 sm:py-20">
        <Container className="max-w-3xl">
          <header className="mb-10">
            <h1 className="font-display text-4xl font-bold tracking-tight text-ink">
              About Bimaya
            </h1>
            <p className="mt-4 text-lg text-muted">
              Bimaya is a digital insurance marketplace built for Nepal. It
              brings insurance shopping online — browse options, compare prices
              and coverage, and buy the plan that fits you, all from your phone
              or computer, without visiting an agent.
            </p>
          </header>

          <section className="mb-10">
            <h2 className="font-display text-2xl font-semibold text-ink">
              Why Bimaya exists
            </h2>
            <p className="mt-3 text-muted">
              There has been no single place in Nepal to compare insurance
              across companies. Information is scattered and often only
              available through agents, and buying is slow and paper-heavy.
              Bimaya brings providers together in one marketplace so people can
              make an informed choice and buy in minutes — and so insurers can
              reach customers they could not easily reach before.
            </p>
          </section>

          <section className="mb-10">
            <h2 className="font-display text-2xl font-semibold text-ink">
              Who it&apos;s for
            </h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              {AUDIENCE.map((item) => (
                <div
                  key={item.title}
                  className="rounded-2xl border border-line bg-white p-5 shadow-sm"
                >
                  <h3 className="font-semibold text-ink">{item.title}</h3>
                  <p className="mt-2 text-sm text-muted">{item.body}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="mb-10">
            <h2 className="font-display text-2xl font-semibold text-ink">
              How it works
            </h2>
            <ol className="mt-4 space-y-3">
              {STEPS.map((step, index) => (
                <li key={step} className="flex gap-3">
                  <span className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">
                    {index + 1}
                  </span>
                  <span className="pt-0.5 text-muted">{step}</span>
                </li>
              ))}
            </ol>
          </section>

          <section className="rounded-2xl border border-line bg-white p-6 shadow-sm sm:p-8">
            <h2 className="font-display text-2xl font-semibold text-ink">
              Ready to get started?
            </h2>
            <p className="mt-3 text-muted">
              Browse the marketplace to compare live policies, or reach out if
              you have a question.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link
                href="/policies"
                className="inline-flex items-center rounded-xl bg-brand-600 px-5 py-2.5 font-medium text-white transition hover:bg-brand-700"
              >
                Browse policies
              </Link>
              <Link
                href="/contact"
                className="inline-flex items-center rounded-xl border border-line px-5 py-2.5 font-medium text-ink transition hover:bg-surface"
              >
                Contact us
              </Link>
            </div>
          </section>
        </Container>
      </main>

      <Footer />
    </>
  );
}
