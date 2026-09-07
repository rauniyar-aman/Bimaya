"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { ClaimDocumentList } from "@/components/claims/claim-document-list";
import { CLAIM_STATUS_META } from "@/components/claims/claim-status";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { Textarea } from "@/components/ui/textarea";
import { formatDate } from "@/lib/date";
import { formatNpr } from "@/lib/format";
import {
  api,
  errorMessage,
  fieldErrors,
  type Claim,
  type ClaimPayoutInitiateResult,
  type PaymentGateway,
} from "@/lib/api";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; claims: Claim[] };

/**
 * The provider's claims queue: every claim filed against their policies, worked
 * through the review lifecycle (start review → request info / approve / reject →
 * simulated payout → settled). Rows update in place after each action so a claim
 * stays visible across its post-decision states.
 */
export function ClaimReviewQueue() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    let cancelled = false;
    api.provider
      .listClaims(authFetch)
      .then((page) => {
        if (!cancelled) setState({ phase: "ready", claims: page.results });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch]);

  function handleUpdated(updated: Claim) {
    setState((s) =>
      s.phase === "ready"
        ? {
            ...s,
            claims: s.claims.map((c) => (c.id === updated.id ? updated : c)),
          }
        : s,
    );
  }

  return (
    <section>
      <h2 className="font-display text-xl font-semibold text-ink">Claims</h2>
      <p className="mt-1 text-sm text-muted">
        Claims filed against your policies. Review each one, then approve and pay
        it out or reject it with a reason.
      </p>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-12">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error" className="mt-4">
          We could not load your claims. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.claims.length === 0 && (
        <div className="mt-4 rounded-2xl border border-dashed border-line bg-surface/50 p-10 text-center">
          <h3 className="font-display text-base font-semibold text-ink">
            No claims yet
          </h3>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
            When a customer files a claim against one of your active policies, it
            appears here for review.
          </p>
        </div>
      )}

      {state.phase === "ready" && state.claims.length > 0 && (
        <div className="mt-4 space-y-3">
          {state.claims.map((claim) => (
            <ClaimReviewRow
              key={claim.id}
              claim={claim}
              onUpdated={handleUpdated}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function ClaimReviewRow({
  claim,
  onUpdated,
}: {
  claim: Claim;
  onUpdated: (claim: Claim) => void;
}) {
  const meta = CLAIM_STATUS_META[claim.status];
  const { policy } = claim.purchase;

  return (
    <div className="rounded-xl border border-line bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display font-semibold text-ink">{policy.name}</h3>
            <StatusPill status={meta.variant}>{meta.label}</StatusPill>
          </div>
          <p className="mt-1 text-sm text-muted">
            {policy.category.name} · Claimed {formatNpr(claim.claimed_amount)} ·
            Incident {formatDate(claim.incident_date)}
            {claim.purchase.policy_number
              ? ` · Policy no. ${claim.purchase.policy_number}`
              : ""}
          </p>
        </div>
      </div>

      <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
        <div className="flex gap-1.5">
          <dt className="text-muted">Filed:</dt>
          <dd className="text-ink">{formatDate(claim.created_at)}</dd>
        </div>
        {claim.incident_location && (
          <div className="flex gap-1.5">
            <dt className="text-muted">Location:</dt>
            <dd className="text-ink">{claim.incident_location}</dd>
          </div>
        )}
      </dl>

      <div className="mt-3">
        <p className="text-xs text-muted">What happened</p>
        <p className="mt-1 whitespace-pre-line text-sm text-ink">
          {claim.description}
        </p>
      </div>

      <div className="mt-4">
        <p className="mb-2 text-xs text-muted">Documents</p>
        <ClaimDocumentList claimId={claim.id} documents={claim.documents} />
      </div>

      <ClaimActions claim={claim} onUpdated={onUpdated} />
    </div>
  );
}

function ClaimActions({
  claim,
  onUpdated,
}: {
  claim: Claim;
  onUpdated: (claim: Claim) => void;
}) {
  switch (claim.status) {
    case "SUBMITTED":
      return <StartReviewAction claim={claim} onUpdated={onUpdated} />;
    case "UNDER_REVIEW":
      return <ReviewDecisionActions claim={claim} onUpdated={onUpdated} />;
    case "MORE_INFO":
      return (
        <ActionNotice tone="pending">
          Sent back to the customer for more information.
          {claim.review_note ? ` You asked: ${claim.review_note}` : ""} Waiting
          for them to resubmit.
        </ActionNotice>
      );
    case "APPROVED":
      return <PayoutAction claim={claim} onUpdated={onUpdated} />;
    case "REJECTED":
      return (
        <ActionNotice tone="muted">
          Rejected.{claim.review_note ? ` ${claim.review_note}` : ""}
        </ActionNotice>
      );
    case "SETTLED":
      return <SettledNotice claim={claim} />;
    default:
      return null;
  }
}

function StartReviewAction({
  claim,
  onUpdated,
}: {
  claim: Claim;
  onUpdated: (claim: Claim) => void;
}) {
  const { authFetch } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function start() {
    setBusy(true);
    setError("");
    try {
      onUpdated(await api.provider.startReviewClaim(authFetch, claim.id));
    } catch (err) {
      setError(errorMessage(err, "Could not start the review. Please try again."));
      setBusy(false);
    }
  }

  return (
    <div className="mt-4 space-y-2 border-t border-line pt-4">
      {error && <Alert variant="error">{error}</Alert>}
      <Button size="sm" loading={busy} onClick={start}>
        Start review
      </Button>
    </div>
  );
}

function ReviewDecisionActions({
  claim,
  onUpdated,
}: {
  claim: Claim;
  onUpdated: (claim: Claim) => void;
}) {
  const { authFetch } = useAuth();
  const [mode, setMode] = useState<"approve" | "info" | "reject" | null>(null);
  const [note, setNote] = useState("");
  const [amount, setAmount] = useState(claim.claimed_amount);
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");

  function reset() {
    setMode(null);
    setNote("");
    setAmount(claim.claimed_amount);
    setErrors({});
    setFormError("");
  }

  async function run(fn: () => Promise<Claim>) {
    setBusy(true);
    setErrors({});
    setFormError("");
    try {
      onUpdated(await fn());
    } catch (err) {
      setErrors(fieldErrors(err));
      setFormError(
        errorMessage(err, "Could not update this claim. Please try again."),
      );
      setBusy(false);
    }
  }

  function confirm() {
    if (mode === "approve")
      return run(() =>
        api.provider.approveClaim(authFetch, claim.id, {
          approved_amount: amount.trim(),
          note: note.trim() || undefined,
        }),
      );
    if (mode === "info")
      return run(() =>
        api.provider.requestInfoClaim(authFetch, claim.id, note.trim()),
      );
    if (mode === "reject")
      return run(() =>
        api.provider.rejectClaim(authFetch, claim.id, note.trim()),
      );
  }

  if (mode === null) {
    return (
      <div className="mt-4 flex flex-wrap gap-2.5 border-t border-line pt-4">
        <Button size="sm" variant="success" onClick={() => setMode("approve")}>
          Approve
        </Button>
        <Button size="sm" variant="secondary" onClick={() => setMode("info")}>
          Request more info
        </Button>
        <Button size="sm" variant="outline" onClick={() => setMode("reject")}>
          Reject
        </Button>
      </div>
    );
  }

  const confirmLabel =
    mode === "approve"
      ? "Approve claim"
      : mode === "info"
        ? "Send back for info"
        : "Reject claim";

  return (
    <div className="mt-4 space-y-4 border-t border-line pt-4">
      {formError && <Alert variant="error">{formError}</Alert>}

      {mode === "approve" && (
        <Field
          label="Approved amount (Rs)"
          htmlFor={`approve_amount_${claim.id}`}
          error={errors.approved_amount}
          hint="The payout amount. Defaults to the amount claimed."
          required
        >
          <Input
            id={`approve_amount_${claim.id}`}
            inputMode="decimal"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            disabled={busy}
            aria-invalid={Boolean(errors.approved_amount)}
          />
        </Field>
      )}

      {(mode === "info" || mode === "reject") && (
        <Field
          label={
            mode === "info"
              ? "What do you need from the customer?"
              : "Reason for rejection"
          }
          htmlFor={`note_${claim.id}`}
          error={errors.note}
          required
        >
          <Textarea
            id={`note_${claim.id}`}
            rows={3}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            disabled={busy}
            aria-invalid={Boolean(errors.note)}
          />
        </Field>
      )}

      {mode === "approve" && (
        <Field
          label="Note (optional)"
          htmlFor={`approve_note_${claim.id}`}
          error={errors.note}
        >
          <Textarea
            id={`approve_note_${claim.id}`}
            rows={2}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            disabled={busy}
          />
        </Field>
      )}

      <div className="flex flex-wrap gap-2.5">
        <Button
          size="sm"
          variant={mode === "reject" ? "outline" : "primary"}
          loading={busy}
          onClick={confirm}
        >
          {confirmLabel}
        </Button>
        <Button size="sm" variant="ghost" onClick={reset} disabled={busy}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

function PayoutAction({
  claim,
  onUpdated,
}: {
  claim: Claim;
  onUpdated: (claim: Claim) => void;
}) {
  const { authFetch } = useAuth();
  // A payout may already be initiated (e.g. the page was reloaded mid-flow);
  // pick it up so the provider can go straight to confirming it.
  const pending = claim.payouts.find((p) => p.status === "INITIATED");
  const [gateway, setGateway] = useState<PaymentGateway>(
    pending?.gateway ?? "ESEWA",
  );
  const [session, setSession] = useState<ClaimPayoutInitiateResult | null>(
    pending
      ? {
          payout_id: pending.id,
          gateway: pending.gateway,
          amount: pending.amount,
          reference: pending.gateway_reference ?? `SIMPAYOUT-${pending.id}`,
          status: "INITIATED",
          simulated: true,
        }
      : null,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function initiate() {
    setBusy(true);
    setError("");
    try {
      setSession(
        await api.provider.payoutInitiateClaim(authFetch, claim.id, gateway),
      );
    } catch (err) {
      setError(errorMessage(err, "Could not start the payout. Please try again."));
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      onUpdated(
        await api.provider.payoutConfirmClaim(
          authFetch,
          claim.id,
          session.payout_id,
        ),
      );
    } catch (err) {
      setError(errorMessage(err, "Could not confirm the payout. Please try again."));
      setBusy(false);
    }
  }

  return (
    <div className="mt-4 space-y-4 border-t border-line pt-4">
      <p className="text-sm">
        <span className="text-muted">Approved for </span>
        <span className="font-display font-semibold text-ink">
          {formatNpr(claim.approved_amount ?? "0")}
        </span>
        <span className="text-muted">
          {" "}
          · settle via a simulated gateway (no real money moves).
        </span>
      </p>

      {error && <Alert variant="error">{error}</Alert>}

      {!session ? (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <Field
            label="Payout gateway"
            htmlFor={`gateway_${claim.id}`}
            className="sm:max-w-xs sm:flex-1"
          >
            <Select
              id={`gateway_${claim.id}`}
              value={gateway}
              onChange={(e) => setGateway(e.target.value as PaymentGateway)}
              disabled={busy}
            >
              <option value="ESEWA">eSewa</option>
              <option value="KHALTI">Khalti</option>
            </Select>
          </Field>
          <Button
            size="sm"
            loading={busy}
            onClick={initiate}
            className="sm:mb-0.5"
          >
            Initiate payout
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="rounded-lg border border-line bg-surface/50 px-4 py-3 text-sm">
            <p className="text-ink">
              Simulated payout ready via{" "}
              <span className="font-medium">{session.gateway}</span>.
            </p>
            <p className="mt-0.5 text-muted">
              Reference {session.reference} · {formatNpr(session.amount)}
            </p>
          </div>
          <Button size="sm" variant="success" loading={busy} onClick={confirm}>
            Confirm payout &amp; settle
          </Button>
        </div>
      )}
    </div>
  );
}

function SettledNotice({ claim }: { claim: Claim }) {
  const payout = claim.payouts.find((p) => p.status === "SUCCESS");
  return (
    <ActionNotice tone="success">
      Settled
      {payout ? ` — ${formatNpr(payout.amount)} paid via ${payout.gateway}` : ""}
      {payout?.gateway_reference ? ` (ref ${payout.gateway_reference})` : ""}.
    </ActionNotice>
  );
}

function ActionNotice({
  tone,
  children,
}: {
  tone: "success" | "pending" | "muted";
  children: React.ReactNode;
}) {
  const toneClass =
    tone === "success"
      ? "text-emerald-700"
      : tone === "pending"
        ? "text-amber-700"
        : "text-muted";
  return (
    <p className={`mt-4 border-t border-line pt-4 text-sm ${toneClass}`}>
      {children}
    </p>
  );
}
