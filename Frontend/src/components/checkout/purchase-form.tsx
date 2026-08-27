"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { LockIcon, WalletIcon } from "@/components/icons";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  api,
  errorMessage,
  fieldErrors,
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

export function PurchaseForm({ policy }: { policy: Policy }) {
  const { authFetch } = useAuth();

  const [nomineeName, setNomineeName] = useState("");
  const [nomineeRelationship, setNomineeRelationship] = useState("");
  const [nomineeContact, setNomineeContact] = useState("");

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [pendingGateway, setPendingGateway] = useState<PaymentGateway | null>(null);

  async function pay(gateway: PaymentGateway) {
    setErrors({});
    setFormError("");
    setPendingGateway(gateway);

    try {
      const purchase = await api.purchases.create(authFetch, {
        policy: policy.id,
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

  return (
    <div className="space-y-5">
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
          label="Relationship to you"
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
          <p className="font-display text-2xl font-bold text-brand-600">
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
    </div>
  );
}
