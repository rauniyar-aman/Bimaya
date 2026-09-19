import Link from "next/link";
import { RedirectSignedInHome } from "@/components/auth/redirect-signed-in-home";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Container } from "@/components/layout/container";
import { buttonVariants } from "@/components/ui/button";
import {
  BadgeCheckIcon,
  CarIcon,
  HealthIcon,
  HeartIcon,
  LockIcon,
  PlaneIcon,
  WalletIcon,
} from "@/components/icons";
import { formatNpr } from "@/lib/format";
import type { ComponentType, SVGProps } from "react";

type IconType = ComponentType<SVGProps<SVGSVGElement>>;

/**
 * The comparison that opens the page. These are illustrative figures, not live
 * listings — the insurer names are Bimaya's own sample providers rather than
 * real Nepali companies, so no real insurer is quoted a price it did not set.
 * Swap for `/api/v1/policies/` data once the marketplace carries live plans.
 */
const EXAMPLE_COVER = 500000;

const EXAMPLE_PLANS: {
  provider: string;
  premium: number;
  benefit: string;
}[] = [
  {
    provider: "Everest Life",
    premium: 1200,
    benefit: "Cashless at 200+ partner hospitals",
  },
  {
    provider: "Himal Assurance",
    premium: 1450,
    benefit: "Free annual health check included",
  },
  {
    provider: "Annapurna General",
    premium: 1690,
    benefit: "Cover across both Nepal and India",
  },
];

const CATEGORIES: {
  slug: string;
  name: string;
  description: string;
  Icon: IconType;
}[] = [
  {
    slug: "life",
    name: "Life",
    description: "Term and endowment cover, so your family keeps its footing.",
    Icon: HeartIcon,
  },
  {
    slug: "health",
    name: "Health",
    description: "Cashless hospital treatment and medical expense cover.",
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
    description: "Medical care, lost baggage and delays while you are abroad.",
    Icon: PlaneIcon,
  },
];

const STEPS: { title: string; description: string }[] = [
  {
    title: "Compare",
    description:
      "Filter by category, premium and cover, then line plans up side by side.",
  },
  {
    title: "Buy online",
    description:
      "Fill in your details and pay with eSewa or Khalti. No paperwork, no queues.",
  },
  {
    title: "Manage and claim",
    description:
      "Track cover, download documents and file claims from your dashboard.",
  },
];

const TRUST: { title: string; description: string; Icon: IconType }[] = [
  {
    title: "Every provider is checked",
    description: "Insurers and plans are reviewed and approved before listing.",
    Icon: BadgeCheckIcon,
  },
  {
    title: "Pay the way you already do",
    description: "eSewa and Khalti, through encrypted checkout.",
    Icon: WalletIcon,
  },
  {
    title: "Documents stay with you",
    description: "Policy papers and receipts in one place, ready to download.",
    Icon: LockIcon,
  },
];

export default function Home() {
  const premiums = EXAMPLE_PLANS.map((plan) => plan.premium);
  const spread = Math.max(...premiums) - Math.min(...premiums);

  return (
    <>
      <RedirectSignedInHome />
      <Navbar />

      <main className="flex-1">
        {/* Hero — the price spread is the argument, so it goes first. */}
        <section>
          <Container className="py-14 lg:py-20">
            <h1 className="max-w-3xl font-display text-5xl leading-[1.05] font-semibold tracking-tight text-ink sm:text-6xl lg:text-7xl">
              Same cover.
              <br />
              Different prices.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">
              An agent shows you one company&apos;s plan. Bimaya shows you the
              market — life, health, vehicle and travel cover from licensed
              Nepali insurers, compared on the numbers that decide it.
            </p>

            <div className="mt-9 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                href="/compare"
                className={buttonVariants({ variant: "cta", size: "lg" })}
              >
                Compare plans
              </Link>
              <Link
                href="/policies"
                className="inline-flex h-12 items-center text-base font-medium text-brand-ink underline-offset-4 hover:underline sm:px-4"
              >
                Browse all policies
              </Link>
            </div>
          </Container>

          {/* The comparison itself, set as a table of three like-for-like plans. */}
          <div className="border-y border-line bg-surface">
            <Container className="py-12 lg:py-16">
              <p className="max-w-md text-sm leading-relaxed text-muted">
                Health cover of{" "}
                <span className="font-medium text-ink">
                  {formatNpr(EXAMPLE_COVER)}
                </span>
                , priced for a 30-year-old in Kathmandu. Example plans, shown to
                illustrate the spread.
              </p>

              <ol className="mt-8 grid gap-x-10 gap-y-10 sm:grid-cols-3 sm:grid-rows-[auto_auto_auto]">
                {EXAMPLE_PLANS.map((plan) => (
                  <li
                    key={plan.provider}
                    className="grid gap-y-3 border-t-2 border-brand-500 pt-5 sm:row-span-3 sm:grid-rows-subgrid sm:gap-y-0"
                  >
                    <p className="font-medium text-ink">{plan.provider}</p>
                    <p className="font-display text-4xl font-semibold text-ink tabular-nums sm:self-end">
                      {formatNpr(plan.premium)}
                      <span className="ml-1.5 align-baseline font-sans text-base font-normal text-muted">
                        a month
                      </span>
                    </p>
                    <p className="text-sm leading-relaxed text-muted sm:self-start">
                      {plan.benefit}
                    </p>
                  </li>
                ))}
              </ol>

              {/* The takeaway, set as a total row: label left, figure right —
                  the same grammar the dashboard ledger uses. */}
              <div className="mt-10 flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2 border-t border-line pt-5">
                <p className="max-w-sm text-sm leading-relaxed text-muted">
                  The difference between the cheapest and the dearest, for cover
                  that is otherwise the same.
                </p>
                <p className="font-display text-3xl font-semibold text-ink tabular-nums">
                  {formatNpr(spread)}
                  <span className="ml-1.5 align-baseline font-sans text-base font-normal text-muted">
                    a month
                  </span>
                </p>
              </div>
            </Container>
          </div>
        </section>

        {/* Categories — ruled rows, the same ledger language as the dashboard. */}
        <section>
          <Container className="py-16 sm:py-20">
            <h2 className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
              What would you like to protect?
            </h2>

            <ul className="mt-8 border-t border-line">
              {CATEGORIES.map(({ slug, name, description, Icon }) => (
                <li key={slug} className="border-b border-line">
                  <Link
                    href={`/categories/${slug}`}
                    className="group flex flex-col gap-1.5 py-5 transition-colors hover:bg-surface/60 sm:flex-row sm:items-center sm:gap-8"
                  >
                    {/* Icon and name stay together; below `sm` the description
                        drops under them rather than squeezing a third column
                        into a phone's width. */}
                    <div className="flex items-center gap-4 sm:gap-8">
                      <Icon className="h-6 w-6 shrink-0 text-brand-500" />
                      <h3 className="font-display text-xl font-semibold text-ink group-hover:text-brand-ink sm:w-32 sm:text-2xl">
                        {name}
                      </h3>
                    </div>
                    <p className="min-w-0 pl-10 text-sm leading-relaxed text-muted sm:pl-0 sm:text-base">
                      {description}
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          </Container>
        </section>

        {/* How it works — a real sequence, so the numbering earns its place. */}
        <section
          id="how-it-works"
          className="scroll-mt-20 border-y border-line bg-surface"
        >
          <Container className="py-16 sm:py-20">
            <h2 className="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
              From comparison to claim
            </h2>

            <ol className="mt-10 grid gap-10 md:grid-cols-3">
              {STEPS.map((step, i) => (
                <li key={step.title}>
                  <p
                    aria-hidden="true"
                    className="font-display text-3xl font-semibold text-brand-500 tabular-nums"
                  >
                    {i + 1}
                  </p>
                  <h3 className="mt-2 font-display text-xl font-semibold text-ink">
                    {step.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted">
                    {step.description}
                  </p>
                </li>
              ))}
            </ol>
          </Container>
        </section>

        {/* Trust — three plain statements, no tile kit. */}
        <section>
          <Container className="py-16 sm:py-20">
            <ul className="grid gap-10 sm:grid-cols-3">
              {TRUST.map(({ title, description, Icon }) => (
                <li key={title}>
                  <Icon className="h-5 w-5 text-brand-500" />
                  <h2 className="mt-3 font-display text-lg font-semibold text-ink">
                    {title}
                  </h2>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">
                    {description}
                  </p>
                </li>
              ))}
            </ul>
          </Container>
        </section>

        {/* Close — quiet and direct, no band, no blobs. */}
        <section className="border-t border-line">
          <Container className="py-16 sm:py-20">
            <h2 className="max-w-2xl font-display text-4xl leading-tight font-semibold tracking-tight text-ink sm:text-5xl">
              Find out what your cover should cost.
            </h2>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                href="/register"
                className={buttonVariants({ variant: "cta", size: "lg" })}
              >
                Create a free account
              </Link>
              <Link
                href="/policies"
                className="inline-flex h-12 items-center text-base font-medium text-brand-ink underline-offset-4 hover:underline sm:px-4"
              >
                Browse all policies
              </Link>
            </div>
          </Container>
        </section>
      </main>

      <Footer />
    </>
  );
}
