"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Detail, Section } from "@/components/admin/detail-blocks";
import { HistoryTimeline } from "@/components/admin/history-timeline";
import {
  KYC_STATUS_META,
  PURCHASE_STATUS_META,
  ROLE_META,
} from "@/components/admin/status-meta";
import { CLAIM_STATUS_META } from "@/components/claims/claim-status";
import { Alert } from "@/components/ui/alert";
import { Avatar } from "@/components/ui/avatar";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/ui/stat-card";
import { StatusPill } from "@/components/ui/status-pill";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { ApiError, api, type AdminUserDetail } from "@/lib/api";
import { formatDate, formatRelativeTime } from "@/lib/date";
import { formatNpr } from "@/lib/format";

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  PASSPORT: "Passport",
  CITIZENSHIP: "Citizenship",
  NID: "National ID",
};

type State =
  | { phase: "loading" }
  | { phase: "notfound" }
  | { phase: "error" }
  | { phase: "ready"; user: AdminUserDetail };

/** Up to two initials for the avatar fallback. */
function initialsFor(user: AdminUserDetail): string {
  const source = user.full_name?.trim() || user.email.split("@")[0];
  const letters = source
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]);
  return letters.join("").toUpperCase() || "B";
}

/**
 * The admin view of one account: who they are, the records they own (KYC,
 * purchases, claims) and their full merged history. Reached from the users
 * table; deep-linkable at `/admin/users/[id]`.
 */
export function UserDetail({ id }: { id: string }) {
  const { authFetch } = useAuth();
  const numericId = Number(id);
  const validId = Number.isInteger(numericId) && numericId > 0;
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    if (!validId) return;
    let cancelled = false;
    api.admin
      .getUser(authFetch, numericId)
      .then((user) => {
        if (!cancelled) setState({ phase: "ready", user });
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
          href="/admin/users"
          className="underline-offset-4 transition-colors hover:text-brand-600 hover:underline"
        >
          Users
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-ink">
          {resolved.phase === "ready"
            ? resolved.user.full_name || resolved.user.email
            : "User"}
        </span>
      </nav>

      {resolved.phase === "loading" && (
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {resolved.phase === "error" && (
        <Alert variant="error">
          We could not load this user. Please refresh and try again.
        </Alert>
      )}

      {resolved.phase === "notfound" && (
        <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center">
          <h2 className="font-display text-xl font-semibold text-ink">
            User not found
          </h2>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
            This account does not exist, or it has been removed.
          </p>
          <Link
            href="/admin/users"
            className={buttonVariants({
              variant: "secondary",
              size: "md",
              className: "mt-5",
            })}
          >
            Back to users
          </Link>
        </div>
      )}

      {resolved.phase === "ready" && (
        <UserBody user={resolved.user} numericId={numericId} />
      )}
    </div>
  );
}

function UserBody({
  user,
  numericId,
}: {
  user: AdminUserDetail;
  numericId: number;
}) {
  const roleMeta = ROLE_META[user.role];

  return (
    <>
      <div className="flex flex-wrap items-start gap-4">
        <Avatar
          src={user.avatar}
          fallback={initialsFor(user)}
          alt={user.full_name || user.email}
          size="lg"
        />
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
            {user.full_name || "—"}
          </h2>
          <p className="mt-0.5 text-sm text-muted">{user.email}</p>
          <div className="mt-2.5 flex flex-wrap gap-2">
            <StatusPill status={roleMeta.variant}>{roleMeta.label}</StatusPill>
            <StatusPill status={user.is_active ? "active" : "failed"}>
              {user.is_active ? "Active" : "Suspended"}
            </StatusPill>
            <StatusPill status={user.is_verified ? "active" : "pending"}>
              {user.is_verified ? "Email verified" : "Email unverified"}
            </StatusPill>
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Purchases" value={user.purchase_count} />
        <StatCard label="Claims" value={user.claim_count} tone="accent" />
        <StatCard label="KYC records" value={user.kyc_records.length} tone="muted" />
        <StatCard
          label="Last sign-in"
          value={user.last_login ? formatRelativeTime(user.last_login) : "Never"}
          hint={user.last_login ? formatDate(user.last_login) : undefined}
          tone="success"
        />
      </div>

      <Card>
        <CardContent>
          <h3 className="font-display text-lg font-semibold text-ink">
            Account details
          </h3>
          <dl className="mt-4 grid gap-x-8 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
            <Detail label="Phone">{user.phone || "—"}</Detail>
            <Detail label="Email">{user.email}</Detail>
            <Detail label="Role">{roleMeta.label}</Detail>
            <Detail label="Joined">{formatDate(user.date_joined)}</Detail>
            <Detail label="Last sign-in">
              {user.last_login ? formatDate(user.last_login) : "Never"}
            </Detail>
            <Detail label="Account ID">
              <span className="font-mono text-sm">#{user.id}</span>
            </Detail>
          </dl>
        </CardContent>
      </Card>

      <Section title="KYC records" empty={user.kyc_records.length === 0}>
        <Table>
          <THead>
            <TR>
              <TH>Document</TH>
              <TH>Name on document</TH>
              <TH>For</TH>
              <TH>Status</TH>
              <TH>Submitted</TH>
            </TR>
          </THead>
          <TBody>
            {user.kyc_records.map((kyc) => {
              const meta = KYC_STATUS_META[kyc.status];
              return (
                <TR key={kyc.id}>
                  <TD>
                    {DOCUMENT_TYPE_LABELS[kyc.document_type] ?? kyc.document_type}
                  </TD>
                  <TD>{kyc.full_name}</TD>
                  <TD className="text-muted">
                    {kyc.is_self ? "Themselves" : "Beneficiary"}
                  </TD>
                  <TD>
                    <StatusPill status={meta.variant}>{meta.label}</StatusPill>
                  </TD>
                  <TD className="text-muted">{formatDate(kyc.created_at)}</TD>
                </TR>
              );
            })}
          </TBody>
        </Table>
      </Section>

      <Section
        title="Recent purchases"
        hint={
          user.purchase_count > user.recent_purchases.length
            ? `Showing the latest ${user.recent_purchases.length} of ${user.purchase_count}.`
            : undefined
        }
        empty={user.recent_purchases.length === 0}
      >
        <Table>
          <THead>
            <TR>
              <TH>Policy</TH>
              <TH>Status</TH>
              <TH>Policy number</TH>
              <TH>Cover period</TH>
              <TH>Bought</TH>
            </TR>
          </THead>
          <TBody>
            {user.recent_purchases.map((purchase) => {
              const meta = PURCHASE_STATUS_META[purchase.status];
              return (
                <TR key={purchase.id}>
                  <TD className="font-medium">{purchase.policy_name}</TD>
                  <TD>
                    <StatusPill status={meta.variant}>{meta.label}</StatusPill>
                  </TD>
                  <TD className="font-mono text-xs text-muted">
                    {purchase.policy_number || "—"}
                  </TD>
                  <TD className="text-muted">
                    {purchase.start_date
                      ? `${formatDate(purchase.start_date)} – ${formatDate(purchase.end_date)}`
                      : "—"}
                  </TD>
                  <TD className="text-muted">{formatDate(purchase.created_at)}</TD>
                </TR>
              );
            })}
          </TBody>
        </Table>
      </Section>

      <Section
        title="Recent claims"
        hint={
          user.claim_count > user.recent_claims.length
            ? `Showing the latest ${user.recent_claims.length} of ${user.claim_count}.`
            : undefined
        }
        empty={user.recent_claims.length === 0}
      >
        <Table>
          <THead>
            <TR>
              <TH>Policy</TH>
              <TH>Status</TH>
              <TH className="text-right">Claimed</TH>
              <TH className="text-right">Approved</TH>
              <TH>Filed</TH>
            </TR>
          </THead>
          <TBody>
            {user.recent_claims.map((claim) => {
              const meta = CLAIM_STATUS_META[claim.status];
              return (
                <TR key={claim.id}>
                  <TD className="font-medium">{claim.policy_name}</TD>
                  <TD>
                    <StatusPill status={meta.variant}>{meta.label}</StatusPill>
                  </TD>
                  <TD className="text-right tabular-nums">
                    {formatNpr(claim.claimed_amount)}
                  </TD>
                  <TD className="text-right tabular-nums text-muted">
                    {claim.approved_amount ? formatNpr(claim.approved_amount) : "—"}
                  </TD>
                  <TD className="text-muted">{formatDate(claim.created_at)}</TD>
                </TR>
              );
            })}
          </TBody>
        </Table>
      </Section>

      <HistoryTimeline subject="user" id={numericId} />
    </>
  );
}
