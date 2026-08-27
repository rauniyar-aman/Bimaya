"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { PolicyRow } from "@/components/provider/policy-row";
import { Container } from "@/components/layout/container";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { BuildingIcon, PlusIcon } from "@/components/icons";
import {
  api,
  errorCode,
  type KycStatus,
  type ProviderPolicy,
  type ProviderProfile,
} from "@/lib/api";

const KYC_LABEL: Record<
  KycStatus,
  { variant: "active" | "pending" | "failed"; label: string }
> = {
  PENDING: { variant: "pending", label: "KYC pending" },
  VERIFIED: { variant: "active", label: "KYC verified" },
  REJECTED: { variant: "failed", label: "KYC rejected" },
};

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; profile: ProviderProfile | null; policies: ProviderPolicy[] };

export function ProviderDashboard() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.provider
        .getProfile(authFetch)
        .then((profile): ProviderProfile | null => profile)
        .catch((error) => {
          if (errorCode(error) === "provider_profile_missing") return null;
          throw error;
        }),
      api.provider
        .listPolicies(authFetch)
        .then((page) => page.results)
        .catch(() => [] as ProviderPolicy[]),
    ])
      .then(([profile, policies]) => {
        if (!cancelled) setState({ phase: "ready", profile, policies });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch]);

  function handleSubmitted(updated: ProviderPolicy) {
    setState((s) =>
      s.phase === "ready"
        ? {
            ...s,
            policies: s.policies.map((p) => (p.id === updated.id ? updated : p)),
          }
        : s,
    );
  }

  function handleDeleted(id: number) {
    setState((s) =>
      s.phase === "ready"
        ? { ...s, policies: s.policies.filter((p) => p.id !== id) }
        : s,
    );
  }

  return (
    <Container className="flex-1 py-10 lg:py-14">
      <h1 className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
        Provider area
      </h1>
      <p className="mt-1.5 text-sm text-muted">
        Manage your company profile and the plans you list on Bimaya.
      </p>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error" className="mt-8">
          We could not load your provider area. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && (
        <div className="mt-8 space-y-8">
          <ProfileSection profile={state.profile} />

          {state.profile && (
            <PoliciesSection
              approved={state.profile.is_approved}
              policies={state.policies}
              onSubmitted={handleSubmitted}
              onDeleted={handleDeleted}
            />
          )}
        </div>
      )}
    </Container>
  );
}

function ProfileSection({ profile }: { profile: ProviderProfile | null }) {
  if (!profile) {
    return (
      <Card>
        <CardContent className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
              <BuildingIcon className="h-5 w-5" />
            </span>
            <div>
              <h2 className="font-display text-lg font-semibold text-ink">
                Set up your provider profile
              </h2>
              <p className="mt-1 max-w-md text-sm text-muted">
                Add your company details to start listing policies. New providers
                are reviewed before their plans appear publicly.
              </p>
            </div>
          </div>
          <Link
            href="/provider/profile"
            className={buttonVariants({ variant: "cta", size: "md" })}
          >
            Set up profile
          </Link>
        </CardContent>
      </Card>
    );
  }

  const kyc = KYC_LABEL[profile.kyc_status];

  return (
    <Card>
      <CardContent className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
            <BuildingIcon className="h-5 w-5" />
          </span>
          <div>
            <h2 className="font-display text-lg font-semibold text-ink">
              {profile.company_name}
            </h2>
            <div className="mt-2 flex flex-wrap gap-2">
              <StatusPill status={profile.is_approved ? "active" : "pending"}>
                {profile.is_approved ? "Approved to sell" : "Awaiting approval"}
              </StatusPill>
              <StatusPill status={kyc.variant}>{kyc.label}</StatusPill>
            </div>
          </div>
        </div>
        <Link
          href="/provider/profile"
          className={buttonVariants({ variant: "secondary", size: "md" })}
        >
          Edit profile
        </Link>
      </CardContent>
    </Card>
  );
}

function PoliciesSection({
  approved,
  policies,
  onSubmitted,
  onDeleted,
}: {
  approved: boolean;
  policies: ProviderPolicy[];
  onSubmitted: (updated: ProviderPolicy) => void;
  onDeleted: (id: number) => void;
}) {
  return (
    <section>
      <div className="flex items-center justify-between gap-4">
        <h2 className="font-display text-xl font-semibold text-ink">
          Your policies
        </h2>
        <Link
          href="/provider/policies/new"
          className={buttonVariants({ variant: "cta", size: "sm" })}
        >
          <PlusIcon className="h-4 w-4" />
          Add policy
        </Link>
      </div>

      {!approved && (
        <Alert variant="info" className="mt-4">
          Your profile is awaiting approval. You can draft and submit plans now —
          they go live on the marketplace once your company is approved.
        </Alert>
      )}

      {policies.length === 0 ? (
        <div className="mt-4 rounded-2xl border border-dashed border-line bg-surface/50 p-10 text-center">
          <h3 className="font-display text-lg font-semibold text-ink">
            No policies yet
          </h3>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
            Create your first plan and submit it for review to reach customers.
          </p>
          <Link
            href="/provider/policies/new"
            className={buttonVariants({
              variant: "cta",
              size: "md",
              className: "mt-5",
            })}
          >
            Create a policy
          </Link>
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {policies.map((policy) => (
            <PolicyRow
              key={policy.id}
              policy={policy}
              onSubmitted={onSubmitted}
              onDeleted={onDeleted}
            />
          ))}
        </div>
      )}
    </section>
  );
}
