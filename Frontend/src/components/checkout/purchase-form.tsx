"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { LockIcon, WalletIcon } from "@/components/icons";
import { KycForm } from "@/components/kyc/kyc-form";
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
  type CustomerKyc,
  type PaymentGateway,
  type Policy,
} from "@/lib/api";
import { formatNpr } from "@/lib/format";

/** eSewa's v2 form API only accepts a real browser POST, so build one and submit it. */
function submitEsewaForm(url: string, fields: Record<string, string>) {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = url;
  for (const [name, value] of Object.entries(fields)) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
}

type InsuredParty = "self" | "other";

export function PurchaseForm({ policy }: { policy: Policy }) {
  const { authFetch } = useAuth();

  // Who is being insured, and the KYC that will cover them.
  const [insured, setInsured] = useState<InsuredParty>("self");
  const [selfKyc, setSelfKyc] = useState<CustomerKyc | null>(null);
  const [loadingSelf, setLoadingSelf] = useState(true);
  // The KYC id locked in for this purchase (self, or a freshly-created beneficiary).
  const [beneficiaryKycId, setBeneficiaryKycId] = useState<number | null>(null);

  const [nomineeName, setNomineeName] = useState("");
  const [nomineeRelationship, setNomineeRelationship] = useState("");
  const [nomineeContact, setNomineeContact] = useState("");

  const [kycErrors, setKycErrors] = useState<Record<string, string>>({});
  const [kycFormError, setKycFormError] = useState("");

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [pendingGateway, setPendingGateway] = useState<PaymentGateway | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.kyc
      .getSelf(authFetch)
      .then((kyc) => {
        if (!cancelled) setSelfKyc(kyc);
      })
      .catch(() => {
        /* Treat a load failure as "no KYC yet" — the form still lets them fill it. */
      })
      .finally(() => {
        if (!cancelled) setLoadingSelf(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch]);

  // The KYC id to attach: self record for "self", the created beneficiary otherwise.
  const kycId = insured === "self" ? selfKyc?.id ?? null : beneficiaryKycId;
  const kycReady = kycId != null;

  async function saveSelfKyc(form: FormData) {
    setKycErrors({});
    setKycFormError("");
    try {
      const kyc = await api.kyc.saveSelf(authFetch, form);
      setSelfKyc(kyc);
    } catch (error) {
      setKycErrors(fieldErrors(error));
      setKycFormError(errorMessage(error, "We could not save your KYC. Please try again."));
    }
  }

  async function saveBeneficiaryKyc(form: FormData) {
    setKycErrors({});
    setKycFormError("");
    try {
      const kyc = await api.kyc.createBeneficiary(authFetch, form);
      setBeneficiaryKycId(kyc.id);
    } catch (error) {
      setKycErrors(fieldErrors(error));
      setKycFormError(errorMessage(error, "We could not save this KYC. Please try again."));
    }
  }

  async function pay(gateway: PaymentGateway) {
    if (kycId == null) return;
    setErrors({});
    setFormError("");
    setPendingGateway(gateway);

    try {
      const purchase = await api.purchases.create(authFetch, {
        policy: policy.id,
        kyc: kycId,
        insured_is_self: insured === "self",
        nominee_name: nomineeName.trim(),
        nominee_relationship: nomineeRelationship.trim(),
        nominee_contact: nomineeContact.trim(),
      });

      const result = await api.payments.initiate(authFetch, {
        policy_purchase_id: purchase.id,
        gateway,
      });

      if (gateway === "ESEWA" && result.fields) {
        submitEsewaForm(result.payment_url, result.fields);
      } else {
        window.location.href = result.payment_url;
      }
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(
        errorMessage(error, "We could not start your payment. Please try again."),
      );
      setPendingGateway(null);
    }
  }

  const busy = pendingGateway !== null;

  if (loadingSelf) {
    return (
      <div className="flex items-center justify-center py-10">
        <Spinner className="h-5 w-5 text-brand-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Who is this policy for? */}
      <fieldset className="space-y-2" disabled={busy}>
        <legend className="text-sm font-medium text-ink">Who is this policy for?</legend>
        <div className="grid grid-cols-2 gap-2">
          <PartyChoice
            active={insured === "self"}
            onClick={() => setInsured("self")}
            title="Myself"
            hint="Reuse your own KYC"
          />
          <PartyChoice
            active={insured === "other"}
            onClick={() => setInsured("other")}
            title="Someone else"
            hint="Add their KYC"
          />
        </div>
      </fieldset>

      {/* KYC gate */}
      {insured === "self" ? (
        <SelfKycGate kyc={selfKyc} />
      ) : null}

      {/* When we don't yet have a usable KYC id, show the capture form. */}
      {!kycReady && (
        <div className="rounded-xl border border-line p-4">
          <p className="mb-4 text-sm text-muted">
            {insured === "self"
              ? "Complete your KYC once to continue. We'll reuse it next time."
              : "Add the insured person's KYC to continue."}
          </p>
          <KycForm
            key={insured}
            initial={insured === "self" ? selfKyc : null}
            onSubmit={insured === "self" ? saveSelfKyc : saveBeneficiaryKyc}
            fieldErrors={kycErrors}
            formError={kycFormError}
            submitLabel={insured === "self" ? "Save my KYC" : "Save their KYC"}
            footnote="You can pay once this is saved. Our team verifies it after payment."
          />
        </div>
      )}

      {/* Nominee + payment — only once a KYC is attached. */}
      {kycReady && (
        <>
          {formError && <Alert variant="error">{formError}</Alert>}

          <div className="space-y-4">
            <Field
              label="Nominee's full name"
              htmlFor="nominee_name"
              error={errors.nominee_name}
              required
            >
              <Input
                id="nominee_name"
                value={nomineeName}
                onChange={(e) => setNomineeName(e.target.value)}
                placeholder="Sita Sharma"
                aria-invalid={Boolean(errors.nominee_name)}
                disabled={busy}
              />
            </Field>

            <Field
              label="Relationship to insured"
              htmlFor="nominee_relationship"
              error={errors.nominee_relationship}
              required
            >
              <Input
                id="nominee_relationship"
                value={nomineeRelationship}
                onChange={(e) => setNomineeRelationship(e.target.value)}
                placeholder="Spouse"
                aria-invalid={Boolean(errors.nominee_relationship)}
                disabled={busy}
              />
            </Field>

            <Field
              label="Nominee's contact number"
              htmlFor="nominee_contact"
              error={errors.nominee_contact}
              required
            >
              <Input
                id="nominee_contact"
                value={nomineeContact}
                onChange={(e) => setNomineeContact(e.target.value)}
                placeholder="98XXXXXXXX"
                aria-invalid={Boolean(errors.nominee_contact)}
                disabled={busy}
              />
            </Field>
          </div>

          <div className="flex items-center justify-between rounded-xl bg-surface p-4">
            <div>
              <p className="text-xs text-muted">Amount due</p>
              <p className="font-display text-2xl font-bold text-brand-ink">
                {formatNpr(policy.premium)}
              </p>
            </div>
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-brand-500">
              <WalletIcon className="h-5 w-5" />
            </span>
          </div>

          <div className="space-y-2.5">
            <Button
              type="button"
              variant="secondary"
              className="w-full"
              loading={pendingGateway === "ESEWA"}
              disabled={busy && pendingGateway !== "ESEWA"}
              onClick={() => pay("ESEWA")}
            >
              Pay with eSewa
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="w-full"
              loading={pendingGateway === "KHALTI"}
              disabled={busy && pendingGateway !== "KHALTI"}
              onClick={() => pay("KHALTI")}
            >
              Pay with Khalti
            </Button>
          </div>

          <p className="flex items-start gap-2 text-xs text-muted">
            <LockIcon className="mt-0.5 h-4 w-4 shrink-0" />
            You will be redirected to your chosen payment provider to complete this
            transaction securely.
          </p>
        </>
      )}
    </div>
  );
}

function PartyChoice({
  active,
  onClick,
  title,
  hint,
}: {
  active: boolean;
  onClick: () => void;
  title: string;
  hint: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={
        "rounded-xl border p-3 text-left transition-colors " +
        (active
          ? "border-brand-500 bg-brand-50"
          : "border-line bg-card hover:bg-surface")
      }
    >
      <span className="block text-sm font-medium text-ink">{title}</span>
      <span className="block text-xs text-muted">{hint}</span>
    </button>
  );
}

/** Shows the status of the reusable self KYC when buying for yourself. */
function SelfKycGate({ kyc }: { kyc: CustomerKyc | null }) {
  if (!kyc) return null;

  const meta =
    kyc.status === "VERIFIED"
      ? { variant: "active" as const, label: "KYC verified" }
      : kyc.status === "REJECTED"
        ? { variant: "failed" as const, label: "KYC needs attention" }
        : { variant: "pending" as const, label: "KYC pending review" };

  return (
    <div className="flex items-center justify-between rounded-xl border border-line bg-surface/50 p-3">
      <div>
        <p className="text-sm font-medium text-ink">{kyc.full_name}</p>
        <p className="text-xs text-muted">Your saved KYC will be used.</p>
      </div>
      <StatusPill status={meta.variant}>{meta.label}</StatusPill>
    </div>
  );
}
