import type { Metadata } from "next";
import Link from "next/link";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Container } from "@/components/layout/container";
import { buttonVariants } from "@/components/ui/button";
import {
  ArrowRightIcon,
  BadgeCheckIcon,
  BuildingIcon,
  ShieldCheckIcon,
  WalletIcon,
} from "@/components/icons";
import type { ComponentType, SVGProps } from "react";

export const metadata: Metadata = {
  title: "For insurance providers",
  description:
    "Partner with Bimaya to list your policies on Nepal's digital insurance marketplace. Reach more customers, sell online and manage everything in one place.",
};

type IconType = ComponentType<SVGProps<SVGSVGElement>>;

const BENEFITS: { title: string; description: string; Icon: IconType }[] = [
  {
    title: "Reach more customers",
    description:
      "Put your policies in front of buyers comparing plans across Nepal — no storefront needed.",
    Icon: BuildingIcon,
  },
  {
    title: "Sell online, end to end",
    description:
      "Customers buy and pay with eSewa and Khalti through secure checkout. No paperwork, no queues.",
    Icon: WalletIcon,
  },
  {
    title: "A trusted marketplace",
    description:
      "Every provider is verified before listing, so customers shop with confidence in your brand.",
    Icon: ShieldCheckIcon,
  },
  {
    title: "Self-service dashboard",
    description:
      "Create and manage your policies, track purchases and update your profile from one place.",
    Icon: BadgeCheckIcon,
  },
];

const STEPS: { title: string; description: string }[] = [
  {
    title: "Send an enquiry",
    description:
      "Tell us about your company and how to reach you. It takes a minute.",
  },
  {
    title: "We review & contact you",
    description:
      "Our team reviews your details, gets in touch and verifies your company documents.",
  },
  {
    title: "Get onboarded",
    description:
      "Once approved, we set up your provider account so you can start listing policies.",
  },
];

export default function ForProviders() {
  return (
    <>
      <Navbar />

      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-0 -z-10">
            <div className="absolute inset-0 bg-gradient-to-b from-brand-50/70 to-white dark:from-brand-500/10 dark:to-transparent" />
            <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-brand-100/50 blur-3xl" />
            <div className="absolute -bottom-32 left-1/3 h-80 w-80 rounded-full bg-accent-100/40 blur-3xl" />
          </div>

          <Container className="py-16 lg:py-24">
            <div className="max-w-2xl">
              <span className="inline-flex items-center gap-2 rounded-full border border-brand-100 bg-card px-3 py-1 text-xs font-medium text-brand-700 shadow-sm">
                <BuildingIcon className="h-3.5 w-3.5" />
                For insurance providers
              </span>

              <h1 className="mt-5 font-display text-4xl font-bold leading-tight tracking-tight text-ink sm:text-5xl">
                Sell insurance on Nepal&apos;s
                <span className="text-brand-600"> digital marketplace.</span>
              </h1>

              <p className="mt-5 text-lg leading-relaxed text-muted">
                Bimaya connects trusted insurers with customers comparing Life,
                Health, Vehicle and Travel plans across Nepal. List your
                policies, sell online and manage everything from one dashboard.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/for-providers/onboard"
                  className={buttonVariants({ variant: "cta", size: "lg" })}
                >
                  Onboard to the platform
                  <ArrowRightIcon className="h-4 w-4" />
                </Link>
                <Link
                  href="/policies"
                  className={buttonVariants({ variant: "outline", size: "lg" })}
                >
                  Browse the marketplace
                </Link>
              </div>
            </div>
          </Container>
        </section>

        {/* Benefits */}
        <section className="py-16 sm:py-20">
          <Container>
            <div className="max-w-2xl">
              <h2 className="font-display text-3xl font-bold tracking-tight text-ink">
                What you get with Bimaya
              </h2>
              <p className="mt-3 text-muted">
                Everything you need to reach customers and sell online, without
                building it yourself.
              </p>
            </div>

            <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {BENEFITS.map(({ title, description, Icon }) => (
                <div key={title}>
                  <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                    <Icon className="h-5 w-5" />
                  </span>
                  <h3 className="mt-4 font-display text-base font-semibold text-ink">
                    {title}
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">
                    {description}
                  </p>
                </div>
              ))}
            </div>
          </Container>
        </section>

        {/* How onboarding works */}
        <section className="bg-surface py-16 sm:py-20">
          <Container>
            <div className="max-w-2xl">
              <h2 className="font-display text-3xl font-bold tracking-tight text-ink">
                How onboarding works
              </h2>
              <p className="mt-3 text-muted">
                We onboard providers by hand so every insurer on Bimaya is
                verified. Here is what to expect.
              </p>
            </div>

            <div className="mt-10 grid gap-6 md:grid-cols-3">
              {STEPS.map((step, i) => (
                <div
                  key={step.title}
                  className="relative rounded-2xl bg-card p-6 shadow-sm"
                >
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-brand-500 font-display text-base font-bold text-white">
                    {i + 1}
                  </span>
                  <h3 className="mt-4 font-display text-lg font-semibold text-ink">
                    {step.title}
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">
                    {step.description}
                  </p>
                </div>
              ))}
            </div>
          </Container>
        </section>

        {/* CTA band */}
        <section className="py-16 sm:py-20">
          <Container>
            <div className="relative overflow-hidden rounded-3xl bg-brand-600 px-6 py-12 text-center shadow-lg sm:px-12 sm:py-16">
              <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-brand-500/60 blur-2xl" />
              <div className="pointer-events-none absolute -bottom-20 -left-10 h-64 w-64 rounded-full bg-brand-700/60 blur-2xl" />
              <div className="relative">
                <h2 className="font-display text-3xl font-bold tracking-tight text-white sm:text-4xl">
                  Ready to partner with Bimaya?
                </h2>
                <p className="mx-auto mt-3 max-w-xl text-brand-100">
                  Send us an enquiry and our team will get in touch to onboard
                  your company.
                </p>
                <div className="mt-8 flex justify-center">
                  <Link
                    href="/for-providers/onboard"
                    className={buttonVariants({ variant: "cta", size: "lg" })}
                  >
                    Onboard to the platform
                    <ArrowRightIcon className="h-4 w-4" />
                  </Link>
                </div>
              </div>
            </div>
          </Container>
        </section>
      </main>

      <Footer />
    </>
  );
}
