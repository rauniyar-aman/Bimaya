"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import {
  api,
  errorMessage,
  fieldErrors,
  type ProviderIssuanceItem,
} from "@/lib/api";
import { formatNpr } from "@/lib/format";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; items: ProviderIssuanceItem[] };

/** The provider's "awaiting issuance" queue: forwarded purchases they must issue. */
export function IssuanceQueue() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    let cancelled = false;
    api.provider
      .listIssuance(authFetch)
      .then((page) => {
        if (!cancelled) setState({ phase: "ready", items: page.results });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch]);

  function handleIssued(id: number) {
    setState((s) =>
      s.phase === "ready"
        ? { ...s, items: s.items.filter((item) => item.id !== id) }
        : s,
    );
  }

  return (
    <section>
      <h2 className="font-display text-xl font-semibold text-ink">
        Awaiting issuance
      </h2>
      <p className="mt-1 text-sm text-muted">
        Purchases verified by Bimaya and forwarded to you. Enter your policy number
        to issue each one.
      </p>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-12">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error" className="mt-4">
          We could not load your issuance queue. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.items.length === 0 && (
        <div className="mt-4 rounded-2xl border border-dashed border-line bg-surface/50 p-10 text-center">
          <h3 className="font-display text-base font-semibold text-ink">
            Nothing to issue right now
          </h3>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
            When a customer&apos;s payment and KYC are verified, their purchase
            appears here for you to issue.
          </p>
        </div>
      )}

      {state.phase === "ready" && state.items.length > 0 && (
        <div className="mt-4 space-y-3">
          {state.items.map((item) => (
            <IssuanceRow key={item.id} item={item} onIssued={handleIssued} />
          ))}
        </div>
      )}
    </section>
  );
}

function IssuanceRow({
  item,
  onIssued,
}: {
  item: ProviderIssuanceItem;
  onIssued: (id: number) => void;
}) {
  const { authFetch } = useAuth();
  const [policyNumber, setPolicyNumber] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [issuing, setIssuing] = useState(false);

  async function handleIssue(event: React.FormEvent) {
    event.preventDefault();
    setErrors({});
    setFormError("");
    setIssuing(true);
    try {
      await api.provider.issue(authFetch, item.id, policyNumber.trim());
      onIssued(item.id);
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(errorMessage(error, "Could not issue this policy. Please try again."));
      setIssuing(false);
    }
  }

  return (
    <div className="rounded-xl border border-line bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display font-semibold text-ink">{item.policy.name}</h3>
            <StatusPill status="info">Forwarded</StatusPill>
          </div>
          <p className="mt-1 text-sm text-muted">
            {item.policy.category.name} · {formatNpr(item.policy.premium)} premium ·{" "}
            {formatNpr(item.policy.coverage_amount)} cover
          </p>
          <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
            <div className="flex gap-1.5">
              <dt className="text-muted">Insured:</dt>
              <dd className="text-ink">
                {item.insured_is_self ? "Policy holder" : "Beneficiary"}
                {item.kyc ? ` · ${item.kyc.full_name}` : ""}
              </dd>
            </div>
            <div className="flex gap-1.5">
              <dt className="text-muted">KYC:</dt>
              <dd className="text-ink">
                {item.kyc ? item.kyc.status : "Not linked"}
              </dd>
            </div>
            <div className="flex gap-1.5">
              <dt className="text-muted">Nominee:</dt>
              <dd className="text-ink">
                {item.nominee_name} ({item.nominee_relationship})
              </dd>
            </div>
            <div className="flex gap-1.5">
              <dt className="text-muted">Contact:</dt>
              <dd className="text-ink">{item.nominee_contact}</dd>
            </div>
          </dl>
        </div>
      </div>

      <form
        onSubmit={handleIssue}
        className="mt-4 flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-end"
      >
        <Field
          label="Policy number"
          htmlFor={`policy_number_${item.id}`}
          error={errors.policy_number}
          className="flex-1"
        >
          <Input
            id={`policy_number_${item.id}`}
            value={policyNumber}
            onChange={(e) => setPolicyNumber(e.target.value)}
            placeholder="e.g. NLI-2026-000123"
            disabled={issuing}
            aria-invalid={Boolean(errors.policy_number)}
          />
        </Field>
        <Button
          type="submit"
          loading={issuing}
          disabled={!policyNumber.trim()}
          className="sm:mb-0.5"
        >
          Issue policy
        </Button>
      </form>

      {formError && <p className="mt-2 text-sm text-red-600">{formError}</p>}
    </div>
  );
}
