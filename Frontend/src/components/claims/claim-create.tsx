"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { ClaimForm } from "@/components/claims/claim-form";
import { Container } from "@/components/layout/container";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { formatNpr } from "@/lib/format";
import {
  api,
  errorMessage,
  fieldErrors as parseFieldErrors,
  type PolicyPurchase,
} from "@/lib/api";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; active: PolicyPurchase[] };

/**
 * Files a claim. If a `?purchase=` id was passed and it is one of the
 * customer's ACTIVE policies, it is preselected; otherwise the customer picks
 * from their active cover. Only ACTIVE policies can be claimed against.
 */
export function ClaimCreate({ purchaseId }: { purchaseId?: number }) {
  const { authFetch } = useAuth();
  const router = useRouter();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [selectedId, setSelectedId] = useState<number | null>(purchaseId ?? null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.purchases
      .list(authFetch)
      .then((page) => {
        if (cancelled) return;
        const active = page.results.filter((p) => p.status === "ACTIVE");
        setState({ phase: "ready", active });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch]);

  const active = state.phase === "ready" ? state.active : [];
  const selected = active.find((p) => p.id === selectedId) ?? null;

  async function handleSubmit(form: FormData) {
    setFieldErrors({});
    setFormError("");
    try {
      const claim = await api.claims.create(authFetch, form);
      router.push(`/dashboard/claims/${claim.id}`);
    } catch (error) {
      setFieldErrors(parseFieldErrors(error));
      setFormError(
        errorMessage(error, "Could not file your claim. Please try again."),
      );
    }
  }

  return (
    <Container className="flex-1 py-10 lg:py-14">
      <nav aria-label="Breadcrumb" className="text-sm text-muted">
        <Link
          href="/dashboard/claims"
          className="underline-offset-4 transition-colors hover:text-brand-600 hover:underline"
        >
          My claims
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-ink">File a claim</span>
      </nav>

      <h1 className="mt-4 font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
        File a claim
      </h1>
      <p className="mt-1.5 text-sm text-muted">
        Tell us what happened and attach your supporting documents. The insurer
        reviews every claim before it is settled.
      </p>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error" className="mt-8">
          We could not load your policies. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && active.length === 0 && (
        <div className="mt-8 max-w-2xl rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center">
          <h2 className="font-display text-lg font-semibold text-ink">
            No active policy to claim against
          </h2>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
            You can only file a claim on a policy that is active. Once your cover
            is live it will appear here.
          </p>
          <Link
            href="/dashboard/policies"
            className={buttonVariants({
              variant: "secondary",
              size: "md",
              className: "mt-5",
            })}
          >
            View my policies
          </Link>
        </div>
      )}

      {state.phase === "ready" && active.length > 0 && (
        <div className="mt-8 max-w-2xl space-y-6">
          {selected ? (
            <SelectedPurchase
              purchase={selected}
              canChange={active.length > 1}
              onChange={() => setSelectedId(null)}
            />
          ) : (
            <PurchasePicker active={active} onPick={setSelectedId} />
          )}

          {selected && (
            <Card>
              <CardContent>
                <ClaimForm
                  key={selected.id}
                  purchaseId={selected.id}
                  minDate={selected.start_date}
                  onSubmit={handleSubmit}
                  fieldErrors={fieldErrors}
                  formError={formError}
                />
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </Container>
  );
}

function SelectedPurchase({
  purchase,
  canChange,
  onChange,
}: {
  purchase: PolicyPurchase;
  canChange: boolean;
  onChange: () => void;
}) {
  return (
    <Card>
      <CardContent className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs text-muted">Claiming against</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h2 className="font-display font-semibold text-ink">
              {purchase.policy.name}
            </h2>
            <StatusPill status="active">Active</StatusPill>
          </div>
          <p className="mt-1 text-sm text-muted">
            {purchase.policy.provider.company_name}
            {purchase.policy_number ? ` · Policy no. ${purchase.policy_number}` : ""}
          </p>
        </div>
        {canChange && (
          <button
            type="button"
            onClick={onChange}
            className="text-sm font-medium text-brand-600 underline-offset-4 hover:underline"
          >
            Change
          </button>
        )}
      </CardContent>
    </Card>
  );
}

function PurchasePicker({
  active,
  onPick,
}: {
  active: PolicyPurchase[];
  onPick: (id: number) => void;
}) {
  return (
    <div>
      <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-muted">
        Choose a policy
      </h2>
      <div className="mt-3 space-y-3">
        {active.map((purchase) => (
          <button
            key={purchase.id}
            type="button"
            onClick={() => onPick(purchase.id)}
            className="block w-full rounded-xl border border-line bg-white p-4 text-left transition-colors hover:border-brand-200 hover:bg-surface/50"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-display font-semibold text-ink">
                {purchase.policy.name}
              </h3>
              <span aria-hidden="true" className="text-muted">
                →
              </span>
            </div>
            <p className="mt-1 text-sm text-muted">
              {purchase.policy.provider.company_name} ·{" "}
              {formatNpr(purchase.policy.coverage_amount)} cover
              {purchase.policy_number ? ` · Policy no. ${purchase.policy_number}` : ""}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
