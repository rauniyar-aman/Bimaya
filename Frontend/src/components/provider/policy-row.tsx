"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { buttonVariants } from "@/components/ui/button";
import { StatusPill } from "@/components/ui/status-pill";
import { POLICY_STATUS_META } from "@/components/provider/policy-status";
import { api, errorMessage, type ProviderPolicy } from "@/lib/api";
import { formatFrequency, formatNpr, formatTerm } from "@/lib/format";

export function PolicyRow({
  policy,
  onSubmitted,
  onDeleted,
}: {
  policy: ProviderPolicy;
  onSubmitted: (updated: ProviderPolicy) => void;
  onDeleted: (id: number) => void;
}) {
  const { authFetch } = useAuth();
  const [busy, setBusy] = useState<null | "submit" | "delete">(null);
  const [error, setError] = useState("");

  const meta = POLICY_STATUS_META[policy.status];
  const canSubmit = policy.status === "DRAFT" || policy.status === "INACTIVE";

  async function handleSubmit() {
    setError("");
    setBusy("submit");
    try {
      const updated = await api.provider.submitPolicy(authFetch, policy.id);
      onSubmitted(updated);
    } catch (err) {
      setError(errorMessage(err, "Could not submit this policy for review."));
      setBusy(null);
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete "${policy.name}"? This cannot be undone.`)) return;
    setError("");
    setBusy("delete");
    try {
      await api.provider.deletePolicy(authFetch, policy.id);
      onDeleted(policy.id);
    } catch (err) {
      setError(errorMessage(err, "Could not delete this policy."));
      setBusy(null);
    }
  }

  return (
    <div className="rounded-xl border border-line bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display font-semibold text-ink">{policy.name}</h3>
            <StatusPill status={meta.variant}>{meta.label}</StatusPill>
          </div>
          <p className="mt-1 text-sm text-muted">
            {policy.category_detail.name} ·{" "}
            {formatNpr(policy.premium)} {formatFrequency(policy.premium_frequency)}{" "}
            · {formatNpr(policy.coverage_amount)} cover ·{" "}
            {formatTerm(policy.term_months)}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <Link
            href={`/provider/policies/${policy.id}/edit`}
            className={buttonVariants({ variant: "secondary", size: "sm" })}
          >
            Edit
          </Link>
          {canSubmit && (
            <Button
              size="sm"
              onClick={handleSubmit}
              loading={busy === "submit"}
              disabled={busy !== null}
            >
              Submit for review
            </Button>
          )}
          <button
            type="button"
            onClick={handleDelete}
            disabled={busy !== null}
            className="rounded-lg px-2.5 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 disabled:opacity-60"
          >
            {busy === "delete" ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>

      <p className="mt-2 text-xs text-muted">{meta.hint}</p>

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
