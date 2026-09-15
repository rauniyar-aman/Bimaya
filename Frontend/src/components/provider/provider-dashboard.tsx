"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { useProviderPortal } from "@/components/provider/provider-portal";
import { ClaimReviewQueue } from "@/components/provider/claim-review-queue";
import { IssuanceQueue } from "@/components/provider/issuance-queue";
import { PolicyRow } from "@/components/provider/policy-row";
import { ProviderAnalyticsSection } from "@/components/provider/provider-analytics";
import { ProviderPayouts } from "@/components/provider/provider-payouts";
import { ProviderSales } from "@/components/provider/provider-sales";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { BuildingIcon, PlusIcon } from "@/components/icons";
import { api, type KycStatus, type ProviderPolicy, type ProviderProfile } from "@/lib/api";

const KYC_LABEL: Record<
  KycStatus,
  { variant: "active" | "pending" | "failed"; label: string }
> = {
  PENDING: { variant: "pending", label: "KYC pending" },
  VERIFIED: { variant: "active", label: "KYC verified" },
  REJECTED: { variant: "failed", label: "KYC rejected" },
};

/**
 * The provider portal home. The organisation profile and the caller's org
 * permissions come from {@link useProviderPortal}; every section below is gated
 * by the granular permission its API needs, so a Claims Officer never sees the
 * policy list and a Finance Viewer sees payouts read-only. This is display only —
 * the backend authorises every request itself.
 */
export function ProviderDashboard() {
  const { authFetch } = useAuth();
  const { profile, permissions } = useProviderPortal();
  const has = (permission: string) => permissions.includes(permission);
  const canViewPolicies = has("policy.view");

  // Policies are the only dashboard data the portal shell doesn't already hold.
  // `null` = still loading; the policies section only renders when both `profile`
  // and `canViewPolicies` hold, so the fetch below runs exactly when it is shown
  // (roles that can't read policies would 403 anyway).
  const [policies, setPolicies] = useState<ProviderPolicy[] | null>(null);

  useEffect(() => {
    if (!profile || !canViewPolicies) return;
    let cancelled = false;
    api.provider
      .listPolicies(authFetch)
      .then((page) => {
        if (!cancelled) setPolicies(page.results);
      })
      .catch(() => {
        if (!cancelled) setPolicies([]);
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, profile, canViewPolicies]);

  function handleSubmitted(updated: ProviderPolicy) {
    setPolicies((prev) =>
      prev ? prev.map((p) => (p.id === updated.id ? updated : p)) : prev,
    );
  }

  function handleDeleted(id: number) {
    setPolicies((prev) => (prev ? prev.filter((p) => p.id !== id) : prev));
  }

  return (
    <div>
      <h1 className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
        Provider area
      </h1>
      <p className="mt-1.5 text-sm text-muted">
        Manage your company profile and the plans you list on Bimaya.
      </p>

      <div className="mt-8 space-y-8">
        <ProfileSection profile={profile} canEdit={has("company.edit")} />

        {profile && canViewPolicies && (
          <PoliciesSection
            approved={profile.is_approved}
            policies={policies}
            canWrite={has("policy.edit")}
            onSubmitted={handleSubmitted}
            onDeleted={handleDeleted}
          />
        )}

        {profile?.is_approved && (
          <>
            {has("analytics.view") && <ProviderAnalyticsSection />}
            {has("issuance.view") && <IssuanceQueue canWrite={has("issuance.issue")} />}
            {has("claim.view") && <ClaimReviewQueue canWrite={has("claim.review")} />}
            {has("purchase.view") && <ProviderSales />}
            {has("payout.view") && <ProviderPayouts />}
          </>
        )}
      </div>
    </div>
  );
}

function ProfileSection({
  profile,
  canEdit,
}: {
  profile: ProviderProfile | null;
  canEdit: boolean;
}) {
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
          <span className="inline-flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-brand-50 text-brand-600">
            {profile.logo ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={profile.logo}
                alt=""
                className="h-full w-full object-cover"
              />
            ) : (
              <BuildingIcon className="h-5 w-5" />
            )}
          </span>
          <div>
            <h2 className="font-display text-lg font-semibold text-ink">
              {profile.company_name}
            </h2>
            <p className="mt-0.5 text-xs font-medium tabular-nums text-muted">
              {profile.public_id}
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <StatusPill status={profile.is_approved ? "active" : "pending"}>
                {profile.is_approved ? "Approved to sell" : "Awaiting approval"}
              </StatusPill>
              <StatusPill status={kyc.variant}>{kyc.label}</StatusPill>
            </div>
            <p className="mt-2 text-sm text-muted">
              Platform commission:{" "}
              <span className="font-medium text-ink">
                {profile.commission_rate}%
              </span>{" "}
              on each sale
            </p>
          </div>
        </div>
        <Link
          href="/provider/profile"
          className={buttonVariants({ variant: "secondary", size: "md" })}
        >
          {canEdit ? "Edit profile" : "View profile"}
        </Link>
      </CardContent>
    </Card>
  );
}

function PoliciesSection({
  approved,
  policies,
  canWrite,
  onSubmitted,
  onDeleted,
}: {
  approved: boolean;
  policies: ProviderPolicy[] | null;
  canWrite: boolean;
  onSubmitted: (updated: ProviderPolicy) => void;
  onDeleted: (id: number) => void;
}) {
  return (
    <section>
      <div className="flex items-center justify-between gap-4">
        <h2 className="font-display text-xl font-semibold text-ink">
          Your policies
        </h2>
        {canWrite && (
          <Link
            href="/provider/policies/new"
            className={buttonVariants({ variant: "cta", size: "sm" })}
          >
            <PlusIcon className="h-4 w-4" />
            Add policy
          </Link>
        )}
      </div>

      {!approved && (
        <Alert variant="info" className="mt-4">
          Your profile is awaiting approval. You can draft and submit plans now —
          they go live on the marketplace once your company is approved.
        </Alert>
      )}

      {policies === null ? (
        <div className="flex items-center justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      ) : policies.length === 0 ? (
        <div className="mt-4 rounded-2xl border border-dashed border-line bg-surface/50 p-10 text-center">
          <h3 className="font-display text-lg font-semibold text-ink">
            No policies yet
          </h3>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
            {canWrite
              ? "Create your first plan and submit it for review to reach customers."
              : "This organisation has not listed any policies yet."}
          </p>
          {canWrite && (
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
          )}
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {policies.map((policy) => (
            <PolicyRow
              key={policy.id}
              policy={policy}
              canWrite={canWrite}
              onSubmitted={onSubmitted}
              onDeleted={onDeleted}
            />
          ))}
        </div>
      )}
    </section>
  );
}
