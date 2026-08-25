import Link from "next/link";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Container } from "@/components/layout/container";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import { buttonVariants } from "@/components/ui/button";
import {
  ArrowRightIcon,
  BadgeCheckIcon,
  CarIcon,
  CompareIcon,
  HealthIcon,
  HeartIcon,
  LockIcon,
  PlaneIcon,
  ShieldCheckIcon,
  WalletIcon,
} from "@/components/icons";
import type { ComponentType, SVGProps } from "react";

type IconType = ComponentType<SVGProps<SVGSVGElement>>;

const CATEGORIES: {
  slug: string;
  name: string;
  description: string;
  Icon: IconType;
}[] = [
  {
    slug: "life",
    name: "Life",
    description: "Protect your family's future with term and endowment cover.",
    Icon: HeartIcon,
  },
  {
    slug: "health",
    name: "Health",
    description: "Cashless hospital cover and medical expense protection.",
    Icon: HealthIcon,
  },
  {
    slug: "vehicle",
    name: "Vehicle",
    description: "Comprehensive and third-party cover for bikes and cars.",
    Icon: CarIcon,
  },
  {
    slug: "travel",
    name: "Travel",
    description: "Stay covered abroad — medical, baggage and delays.",
    Icon: PlaneIcon,
  },
];

const STEPS: { title: string; description: string }[] = [
  {
    title: "Compare plans",
    description:
      "Filter by category, premium and coverage, then compare plans side by side.",
  },
  {
    title: "Buy online securely",
    description:
      "Complete your details and pay with eSewa or Khalti — no paperwork, no queues.",
  },
  {
    title: "Manage & claim",
    description:
      "Track active policies, download receipts and file claims from your dashboard.",
  },
];

const FEATURES: { title: string; description: string; Icon: IconType }[] = [
  {
    title: "Transparent comparison",
    description: "See premiums, coverage and terms clearly — no hidden surprises.",
    Icon: CompareIcon,
  },
  {
    title: "Verified providers",
    description: "Every provider and policy is reviewed and approved before listing.",
    Icon: BadgeCheckIcon,
  },
  {
    title: "Secure payments",
    description: "Pay safely with eSewa and Khalti through encrypted checkout.",
    Icon: WalletIcon,
  },
  {
    title: "Digital policies",
    description: "Instant digital policy documents and receipts, stored in one place.",
    Icon: LockIcon,
  },
];

export default function Home() {
  return (
    <>
      <Navbar />

      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-0 -z-10">
            <div className="absolute inset-0 bg-gradient-to-b from-brand-50/70 to-white" />
            <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-brand-100/50 blur-3xl" />
            <div className="absolute -bottom-32 left-1/3 h-80 w-80 rounded-full bg-accent-100/40 blur-3xl" />
          </div>

          <Container className="grid items-center gap-12 py-16 lg:grid-cols-2 lg:py-24">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full border border-brand-100 bg-white px-3 py-1 text-xs font-medium text-brand-700 shadow-sm">
                <ShieldCheckIcon className="h-3.5 w-3.5" />
                Nepal&apos;s digital insurance marketplace
              </span>

              <h1 className="mt-5 font-display text-4xl font-bold leading-tight tracking-tight text-ink sm:text-5xl">
                Online insurance,
                <span className="text-brand-600"> made easy.</span>
              </h1>

              <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
                Compare Life, Health, Vehicle and Travel plans from trusted
                providers across Nepal. Buy in minutes and manage everything in
                one place.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link href="/policies" className={buttonVariants({ variant: "cta", size: "lg" })}>
                  Browse policies
                  <ArrowRightIcon className="h-4 w-4" />
                </Link>
                <Link href="/compare" className={buttonVariants({ variant: "outline", size: "lg" })}>
                  Compare plans
                </Link>
              </div>

              <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-muted">
                <span className="inline-flex items-center gap-2">
                  <LockIcon className="h-4 w-4 text-brand-500" />
                  Secure &amp; encrypted
                </span>
                <span className="inline-flex items-center gap-2">
                  <WalletIcon className="h-4 w-4 text-brand-500" />
                  eSewa &amp; Khalti payments
                </span>
              </div>
            </div>

            {/* Product preview */}
            <div className="relative mx-auto w-full max-w-md lg:mx-0">
              <Card className="relative z-10 p-6 shadow-lg">
                <div className="flex items-center justify-between">
                  <Badge>Health</Badge>
                  <StatusPill status="active">Active</StatusPill>
                </div>
                <h3 className="mt-4 font-display text-lg font-semibold text-ink">
                  Nagarik Health Plus
                </h3>
                <p className="mt-1 text-sm text-muted">
                  Cashless cover across 200+ partner hospitals.
                </p>
                <div className="mt-5 grid grid-cols-2 gap-4 rounded-xl bg-surface p-4">
                  <div>
                    <p className="text-xs text-muted">Coverage</p>
                    <p className="font-display text-base font-semibold text-ink">
                      Rs 5,00,000
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted">Term</p>
                    <p className="font-display text-base font-semibold text-ink">
                      1 year
                    </p>
                  </div>
                </div>
                <div className="mt-5 flex items-end justify-between">
                  <div>
                    <p className="text-xs text-muted">Premium</p>
                    <p className="font-display text-2xl font-bold text-brand-600">
                      Rs 1,200
                      <span className="text-sm font-medium text-muted">/mo</span>
                    </p>
                  </div>
                  <Link
                    href="/policies"
                    className={buttonVariants({ variant: "cta", size: "sm" })}
                  >
                    Buy now
                  </Link>
                </div>
              </Card>

              <div className="absolute -bottom-5 -left-5 z-20 hidden rounded-xl border border-line bg-white p-3 shadow-md sm:block">
                <StatusPill status="success">Payment successful</StatusPill>
              </div>
            </div>
          </Container>
        </section>

        {/* Categories */}
        <section className="py-16 sm:py-20">
          <Container>
            <div className="max-w-2xl">
              <h2 className="font-display text-3xl font-bold tracking-tight text-ink">
                Explore insurance categories
              </h2>
              <p className="mt-3 text-muted">
                Whatever you need to protect, find the right cover from providers
                across Nepal.
              </p>
            </div>

            <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {CATEGORIES.map(({ slug, name, description, Icon }) => (
                <Link
                  key={slug}
                  href={`/categories/${slug}`}
                  className="group rounded-2xl border border-line bg-white p-6 shadow-sm transition-all hover:-translate-y-1 hover:border-brand-200 hover:shadow-md"
                >
                  <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                    <Icon className="h-6 w-6" />
                  </span>
                  <h3 className="mt-4 font-display text-lg font-semibold text-ink">
                    {name}
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">
                    {description}
                  </p>
                  <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-brand-600">
                    View plans
                    <ArrowRightIcon className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                  </span>
                </Link>
              ))}
            </div>
          </Container>
        </section>

        {/* How it works */}
        <section id="how-it-works" className="scroll-mt-20 bg-surface py-16 sm:py-20">
          <Container>
            <div className="max-w-2xl">
              <h2 className="font-display text-3xl font-bold tracking-tight text-ink">
                How Bimaya works
              </h2>
              <p className="mt-3 text-muted">
                From comparison to claim in three simple steps.
              </p>
            </div>

            <div className="mt-10 grid gap-6 md:grid-cols-3">
              {STEPS.map((step, i) => (
                <div key={step.title} className="relative rounded-2xl bg-white p-6 shadow-sm">
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

        {/* Why Bimaya */}
        <section className="py-16 sm:py-20">
          <Container>
            <div className="max-w-2xl">
              <h2 className="font-display text-3xl font-bold tracking-tight text-ink">
                Why choose Bimaya
              </h2>
              <p className="mt-3 text-muted">
                Built for clarity, trust and convenience.
              </p>
            </div>

            <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {FEATURES.map(({ title, description, Icon }) => (
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

        {/* CTA band */}
        <section className="pb-20">
          <Container>
            <div className="relative overflow-hidden rounded-3xl bg-brand-600 px-6 py-12 text-center shadow-lg sm:px-12 sm:py-16">
              <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-brand-500/60 blur-2xl" />
              <div className="pointer-events-none absolute -bottom-20 -left-10 h-64 w-64 rounded-full bg-brand-700/60 blur-2xl" />
              <div className="relative">
                <h2 className="font-display text-3xl font-bold tracking-tight text-white sm:text-4xl">
                  Ready to find your plan?
                </h2>
                <p className="mx-auto mt-3 max-w-xl text-brand-100">
                  Create a free account and get covered in minutes.
                </p>
                <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
                  <Link href="/register" className={buttonVariants({ variant: "cta", size: "lg" })}>
                    Get started
                    <ArrowRightIcon className="h-4 w-4" />
                  </Link>
                  <Link
                    href="/policies"
                    className="inline-flex h-12 items-center justify-center rounded-lg border border-white/30 px-6 text-base font-medium text-white transition-colors hover:bg-white/10"
                  >
                    Browse policies
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
