"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Detail, Section } from "@/components/admin/detail-blocks";
import { HistoryTimeline } from "@/components/admin/history-timeline";
import {
  KYC_STATUS_META,
  POLICY_STATUS_META,
  PROVIDER_ROLE_META,
} from "@/components/admin/status-meta";
import { Alert } from "@/components/ui/alert";
import { Avatar } from "@/components/ui/avatar";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/ui/stat-card";
import { StatusPill } from "@/components/ui/status-pill";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { ApiError, api, type AdminProviderDetail } from "@/lib/api";
import { formatDate } from "@/lib/date";
import { formatNpr, frequencySuffix } from "@/lib/format";

type State =
  | { phase: "loading" }
  | { phase: "notfound" }
  | { phase: "error" }
  | { phase: "ready"; provider: AdminProviderDetail };

/** Up to two initials from the company name, for the logo fallback. */
function initialsFor(companyName: string): string {
  const letters = companyName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]);
  return letters.join("").toUpperCase() || "B";
}

/**
 * The admin view of one insurance provider: the company record, its team, KYC
 * paperwork, policies and settlement totals, followed by the full merged
 * history. Reached from the providers table; deep-linkable at
 * `/admin/providers/[id]`.
 */
export function ProviderDetail({ id }: { id: string }) {
  const { authFetch } = useAuth();
  const numericId = Number(id);
  const validId = Number.isInteger(numericId) && numericId > 0;
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    if (!validId) return;
    let cancelled = false;
    api.admin
      .getProvider(authFetch, numericId)
      .then((provider) => {
        if (!cancelled) setState({ phase: "ready", provider });
      })
      .catch((error) => {
        if (cancelled) return;
        setState(
          error instanceof ApiError && error.status === 404
            ? { phase: "notfound" }
            : { phase: "error" },
        );
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, numericId, validId]);

  const resolved: State = validId ? state : { phase: "notfound" };

  return (
    <div className="space-y-6">
      <nav aria-label="Breadcrumb" className="text-sm text-muted">
        <Link
          href="/admin/providers"
          className="underline-offset-4 transition-colors hover:text-brand-ink hover:underline"
        >
          Providers
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-ink">
          {resolved.phase === "ready" ? resolved.provider.company_name : "Provider"}
        </span>
      </nav>

      {resolved.phase === "loading" && (
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {resolved.phase === "error" && (
        <Alert variant="error">
          We could not load this provider. Please refresh and try again.
        </Alert>
      )}

      {resolved.phase === "notfound" && (
        <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center">
          <h2 className="font-display text-xl font-semibold text-ink">
            Provider not found
          </h2>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
            This organisation does not exist, or it has been removed.
          </p>
          <Link
            href="/admin/providers"
            className={buttonVariants({
              variant: "secondary",
              size: "md",
              className: "mt-5",
            })}
          >
            Back to providers
          </Link>
        </div>
      )}

      {resolved.phase === "ready" && (
        <ProviderBody provider={resolved.provider} numericId={numericId} />
      )}
    </div>
  );
}

function ProviderBody({
  provider,
  numericId,
}: {
  provider: AdminProviderDetail;
  numericId: number;
}) {
  const kycMeta = KYC_STATUS_META[provider.kyc_status];

  return (
    <>
      <div className="flex flex-wrap items-start gap-4">
        <Avatar
          src={provider.logo}
          fallback={initialsFor(provider.company_name)}
          alt={provider.company_name}
          size="lg"
          shape="square"
        />
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
            {provider.company_name}
          </h2>
          <p className="mt-0.5 text-sm text-muted">
            <span className="font-mono">{provider.public_id}</span> ·{" "}
            {provider.owner_email}
          </p>
          <div className="mt-2.5 flex flex-wrap gap-2">
            <StatusPill status={provider.is_approved ? "active" : "pending"}>
              {provider.is_approved ? "Approved" : "Awaiting approval"}
            </StatusPill>
            <StatusPill status={kycMeta.variant}>KYC {kycMeta.label}</StatusPill>
          </div>
        </div>
      </div>

      {provider.description && (
        <p className="max-w-3xl text-sm text-muted">{provider.description}</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Policies"
          value={provider.policy_count}
          hint={`${provider.active_policies} approved`}
        />
        <StatCard
          label="Purchases"
          value={provider.purchase_count}
          tone="accent"
        />
        <StatCard
          label="Pending claims"
          value={provider.pending_claims}
          hint="Awaiting a decision"
          tone="muted"
        />
        <StatCard
          label="Payouts owed"
          value={formatNpr(provider.payout_net_total)}
          hint="Net of platform commission"
          tone="success"
        />
      </div>

      <Card>
        <CardContent>
          <h3 className="font-display text-lg font-semibold text-ink">
            Company details
          </h3>
          <dl className="mt-4 grid gap-x-8 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
            <Detail label="Registration number">
              {provider.registration_number || "—"}
            </Detail>
            <Detail label="Owner">
              <div>{provider.owner_name || "—"}</div>
              <div className="text-xs text-muted">{provider.owner_email}</div>
            </Detail>
            <Detail label="Commission rate">
              <span className="tabular-nums">{provider.commission_rate}%</span>
            </Detail>
            <Detail label="Support email">{provider.support_email || "—"}</Detail>
            <Detail label="Support phone">{provider.support_phone || "—"}</Detail>
            <Detail label="Website">
              {provider.website ? (
                <a
                  href={provider.website}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="text-brand-ink underline-offset-4 hover:underline"
                >
                  {provider.website}
                </a>
              ) : (
                "—"
              )}
            </Detail>
            <Detail label="Onboarded">{formatDate(provider.created_at)}</Detail>
            <Detail label="Last updated">{formatDate(provider.updated_at)}</Detail>
            <Detail label="Public ID">
              <span className="font-mono text-sm">{provider.public_id}</span>
            </Detail>
          </dl>
        </CardContent>
      </Card>

      <Section
        title="Team"
        empty={provider.memberships.length === 0}
        emptyLabel="No one has been added to this organisation yet."
      >
        <Table>
          <THead>
            <TR>
              <TH>Member</TH>
              <TH>Role</TH>
              <TH>Status</TH>
              <TH>Joined</TH>
            </TR>
          </THead>
          <TBody>
            {provider.memberships.map((member) => {
              const roleMeta = PROVIDER_ROLE_META[member.role];
              return (
                <TR key={member.user_id}>
                  <TD>
                    <div className="font-medium text-ink">
                      {member.full_name || "—"}
                    </div>
                    <div className="text-xs text-muted">{member.email}</div>
                  </TD>
                  <TD>
                    <StatusPill status={roleMeta.variant}>
                      {roleMeta.label}
                    </StatusPill>
                  </TD>
                  <TD>
                    <StatusPill status={member.is_active ? "active" : "failed"}>
                      {member.is_active ? "Active" : "Suspended"}
                    </StatusPill>
                  </TD>
                  <TD className="text-muted">{formatDate(member.date_joined)}</TD>
                </TR>
              );
            })}
          </TBody>
        </Table>
      </Section>

      <Section
        title="KYC documents"
        empty={provider.kyc_documents.length === 0}
        emptyLabel="No compliance paperwork has been uploaded yet."
      >
        <Table>
          <THead>
            <TR>
              <TH>Document</TH>
              <TH>File</TH>
              <TH>Status</TH>
              <TH>Uploaded by</TH>
              <TH>Reviewed</TH>
            </TR>
          </THead>
          <TBody>
            {provider.kyc_documents.map((document) => (
              <TR key={document.id}>
                <TD className="font-medium">{document.document_type_display}</TD>
                <TD className="text-muted">{document.file_name}</TD>
                <TD>
                  <StatusPill status={KYC_STATUS_META[document.status].variant}>
                    {document.status_display}
                  </StatusPill>
                </TD>
                <TD className="text-muted">
                  {document.uploaded_by_email || "—"}
                </TD>
                <TD className="text-muted">{formatDate(document.reviewed_at)}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </Section>

      <Section
        title="Recent policies"
        hint={
          provider.policy_count > provider.recent_policies.length
            ? `Showing the latest ${provider.recent_policies.length} of ${provider.policy_count}.`
            : undefined
        }
        empty={provider.recent_policies.length === 0}
        emptyLabel="This provider has not listed a policy yet."
      >
        <Table>
          <THead>
            <TR>
              <TH>Policy</TH>
              <TH>Status</TH>
              <TH className="text-right">Premium</TH>
              <TH className="text-right">Coverage</TH>
              <TH>Created</TH>
            </TR>
          </THead>
          <TBody>
            {provider.recent_policies.map((policy) => {
              const meta = POLICY_STATUS_META[policy.status];
              return (
                <TR key={policy.id}>
                  <TD className="font-medium">{policy.name}</TD>
                  <TD>
                    <StatusPill status={meta.variant}>{meta.label}</StatusPill>
                  </TD>
                  <TD className="text-right tabular-nums">
                    {formatNpr(policy.premium)}
                    <span className="text-muted">
                      {frequencySuffix(policy.premium_frequency)}
                    </span>
                  </TD>
                  <TD className="text-right tabular-nums">
                    {formatNpr(policy.coverage_amount)}
                  </TD>
                  <TD className="text-muted">{formatDate(policy.created_at)}</TD>
                </TR>
              );
            })}
          </TBody>
        </Table>
      </Section>

      <HistoryTimeline subject="provider" id={numericId} />
    </>
  );
}
