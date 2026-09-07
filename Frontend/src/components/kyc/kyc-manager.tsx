"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { KycForm } from "@/components/kyc/kyc-form";
import { Alert } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import type { StatusVariant } from "@/components/ui/status-pill";
import {
  api,
  errorMessage,
  fieldErrors,
  type CustomerKyc,
  type KycStatus,
} from "@/lib/api";

const KYC_PILL: Record<KycStatus, { variant: StatusVariant; label: string }> = {
  PENDING: { variant: "pending", label: "Pending review" },
  VERIFIED: { variant: "active", label: "Verified" },
  REJECTED: { variant: "failed", label: "Needs attention" },
};

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; kyc: CustomerKyc | null };

export function KycManager() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.kyc
      .getSelf(authFetch)
      .then((kyc) => {
        if (!cancelled) setState({ phase: "ready", kyc });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch]);

  async function handleSubmit(form: FormData) {
    setErrors({});
    setFormError("");
    setSaved(false);
    try {
      const kyc = await api.kyc.saveSelf(authFetch, form);
      setState({ phase: "ready", kyc });
      setSaved(true);
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(errorMessage(error, "We could not save your KYC. Please try again."));
    }
  }

  if (state.phase === "loading") {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner className="h-6 w-6 text-brand-500" />
      </div>
    );
  }

  if (state.phase === "error") {
    return (
      <Alert variant="error" className="mt-8">
        We could not load your KYC. Please refresh and try again.
      </Alert>
    );
  }

  const { kyc } = state;
  const pill = kyc ? KYC_PILL[kyc.status] : null;

  return (
    <div className="mt-8 max-w-2xl space-y-6">
      {pill && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted">Current status</span>
          <StatusPill status={pill.variant}>{pill.label}</StatusPill>
        </div>
      )}

      {saved && (
        <Alert variant="success">
          Your KYC has been submitted and is pending review. You can update it any
          time — changes are re-reviewed.
        </Alert>
      )}

      {kyc?.status === "VERIFIED" && !saved && (
        <Alert variant="info">
          Your KYC is verified and reused for your own purchases. Editing it sends
          it back for re-review.
        </Alert>
      )}

      <Card>
        <CardContent>
          <KycForm
            initial={kyc}
            onSubmit={handleSubmit}
            fieldErrors={errors}
            formError={formError}
            submitLabel={kyc ? "Update KYC" : "Submit KYC"}
          />
        </CardContent>
      </Card>
    </div>
  );
}
