"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth/auth-provider";
import { Container } from "@/components/layout/container";
import {
  BadgeCheckIcon,
  CompareIcon,
  ShieldCheckIcon,
} from "@/components/icons";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import { ROLE_LABELS, firstName } from "@/lib/user";

const NEXT_STEPS = [
  {
    Icon: ShieldCheckIcon,
    title: "Browse policies",
    body: "See what licensed Nepali insurers offer for Life, Health, Vehicle and Travel cover.",
    href: "/policies",
    action: "Browse policies",
  },
  {
    Icon: CompareIcon,
    title: "Compare side by side",
    body: "Line up premiums, coverage and add-ons so you can see the real difference.",
    href: "/compare",
    action: "Compare plans",
  },
];

function formatJoined(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function DashboardOverview() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <Container className="flex-1 py-10 lg:py-14">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
            Namaste, {firstName(user)}
          </h1>
          <p className="mt-1.5 text-sm text-muted">
            Here is your Bimaya account at a glance.
          </p>
        </div>
        <StatusPill status={user.is_verified ? "active" : "pending"}>
          {user.is_verified ? "Verified account" : "Verification pending"}
        </StatusPill>
      </div>

      {!user.is_verified && (
        <Alert variant="error" className="mt-6">
          Your account is not verified yet.{" "}
          <Link
            href={`/verify-otp?email=${encodeURIComponent(user.email)}`}
            className="font-medium underline underline-offset-4"
          >
            Enter your verification code
          </Link>{" "}
          to unlock purchases.
        </Alert>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        {/* Policies — nothing to show until the marketplace is stocked. */}
        <Card className="lg:col-span-2">
          <CardContent className="flex flex-col items-start gap-4 py-10 text-center sm:items-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-500">
              <ShieldCheckIcon className="h-6 w-6" />
            </span>
            <div className="sm:text-center">
              <h2 className="font-display text-lg font-semibold text-ink">
                No policies yet
              </h2>
              <p className="mx-auto mt-1.5 max-w-sm text-sm leading-relaxed text-muted">
                Once you buy cover through Bimaya it appears here, with renewal
                dates and downloadable documents.
              </p>
            </div>
            <Link
              href="/policies"
              className={buttonVariants({ variant: "cta", size: "md" })}
            >
              Find your first policy
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <BadgeCheckIcon className="h-5 w-5 text-brand-500" />
              <h2 className="font-display text-base font-semibold text-ink">
                Your details
              </h2>
            </div>

            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-muted">Email</dt>
                <dd className="truncate font-medium text-ink">{user.email}</dd>
              </div>
              <div>
                <dt className="text-muted">Mobile</dt>
                <dd className="font-medium text-ink">
                  {user.phone || "Not added yet"}
                </dd>
              </div>
              <div>
                <dt className="text-muted">Account type</dt>
                <dd className="font-medium text-ink">
                  {ROLE_LABELS[user.role]}
                </dd>
              </div>
              <div>
                <dt className="text-muted">Member since</dt>
                <dd className="font-medium text-ink">
                  {formatJoined(user.date_joined)}
                </dd>
              </div>
            </dl>

            <Link
              href="/dashboard/profile"
              className={buttonVariants({
                variant: "secondary",
                size: "sm",
                className: "w-full",
              })}
            >
              Edit profile
            </Link>
          </CardContent>
        </Card>
      </div>

      <h2 className="mt-12 font-display text-lg font-semibold text-ink">
        Where to next
      </h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {NEXT_STEPS.map(({ Icon, title, body, href, action }) => (
          <Card key={title}>
            <CardContent className="space-y-3">
              <Icon className="h-6 w-6 text-brand-500" />
              <h3 className="font-display text-base font-semibold text-ink">
                {title}
              </h3>
              <p className="text-sm leading-relaxed text-muted">{body}</p>
              <Link
                href={href}
                className="inline-flex text-sm font-medium text-brand-600 underline-offset-4 hover:underline"
              >
                {action} →
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>
    </Container>
  );
}
