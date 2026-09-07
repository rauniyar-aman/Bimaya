"use client";

import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { FileInput } from "@/components/ui/file-input";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type {
  CustomerKyc,
  CustomerKycInput,
  DocumentType,
  MaritalStatus,
} from "@/lib/api";

const DOCUMENT_TYPES: { value: DocumentType; label: string }[] = [
  { value: "NID", label: "National ID card (NID)" },
  { value: "CITIZENSHIP", label: "Citizenship" },
  { value: "PASSPORT", label: "Passport" },
];

const MARITAL_STATUSES: { value: MaritalStatus; label: string }[] = [
  { value: "SINGLE", label: "Single" },
  { value: "MARRIED", label: "Married" },
  { value: "OTHER", label: "Other" },
];

/** Human copy for the image inputs, keyed by document type. */
function imageHelp(documentType: DocumentType): {
  frontLabel: string;
  backLabel: string | null;
  backRequired: boolean;
} {
  switch (documentType) {
    case "PASSPORT":
      return { frontLabel: "Passport photo page", backLabel: null, backRequired: false };
    case "CITIZENSHIP":
      return {
        frontLabel: "Citizenship — front",
        backLabel: "Citizenship — back",
        backRequired: true,
      };
    case "NID":
    default:
      return {
        frontLabel: "National ID — front",
        backLabel: "National ID — back (optional)",
        backRequired: false,
      };
  }
}

export interface KycFormProps {
  /** Existing record to prefill (self KYC edit); omit for a fresh capture. */
  initial?: CustomerKyc | null;
  /** Called with a built FormData once client-side checks pass. */
  onSubmit: (form: FormData) => Promise<void>;
  /** Field errors from the API (server-side validation). */
  fieldErrors?: Record<string, string>;
  /** Top-level error message from the API. */
  formError?: string;
  submitLabel?: string;
  /** Extra note under the submit button (e.g. "you can pay after this"). */
  footnote?: string;
}

/**
 * Collects a customer's KYC: personal details, addresses and an identity
 * document whose required images depend on the chosen document type. Building
 * the multipart payload is left here so both the self-KYC page and the checkout
 * gate can reuse it.
 */
export function KycForm({
  initial,
  onSubmit,
  fieldErrors = {},
  formError,
  submitLabel = "Save KYC",
  footnote,
}: KycFormProps) {
  const [values, setValues] = useState<CustomerKycInput>({
    full_name: initial?.full_name ?? "",
    email: initial?.email ?? "",
    phone: initial?.phone ?? "",
    date_of_birth: initial?.date_of_birth ?? "",
    marital_status: initial?.marital_status ?? "",
    family_details: initial?.family_details ?? "",
    temporary_address: initial?.temporary_address ?? "",
    permanent_address: initial?.permanent_address ?? "",
    document_type: initial?.document_type ?? "NID",
    document_number: initial?.document_number ?? "",
  });
  const [front, setFront] = useState<File | null>(null);
  const [back, setBack] = useState<File | null>(null);
  const [localErrors, setLocalErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const help = imageHelp(values.document_type);
  // When editing, the record already has stored images; a new file is optional.
  const hasStoredFront = Boolean(initial?.document_front);
  const errors = { ...fieldErrors, ...localErrors };

  function set<K extends keyof CustomerKycInput>(key: K, value: CustomerKycInput[K]) {
    setValues((v) => ({ ...v, [key]: value }));
  }

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (!values.full_name.trim()) next.full_name = "Your full name is required.";
    if (!values.permanent_address.trim())
      next.permanent_address = "A permanent address is required.";
    if (!values.document_number.trim())
      next.document_number = "The document number is required.";
    if (!front && !hasStoredFront)
      next.document_front = "An image of your document is required.";
    if (help.backRequired && !back && !initial?.document_back)
      next.document_back = "Both sides of the citizenship are required.";
    setLocalErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!validate()) return;

    const form = new FormData();
    form.set("full_name", values.full_name.trim());
    form.set("email", values.email?.trim() ?? "");
    form.set("phone", values.phone?.trim() ?? "");
    if (values.date_of_birth) form.set("date_of_birth", values.date_of_birth);
    if (values.marital_status) form.set("marital_status", values.marital_status);
    form.set("family_details", values.family_details?.trim() ?? "");
    form.set("temporary_address", values.temporary_address?.trim() ?? "");
    form.set("permanent_address", values.permanent_address.trim());
    form.set("document_type", values.document_type);
    form.set("document_number", values.document_number.trim());
    if (front) form.set("document_front", front);
    if (back) form.set("document_back", back);

    setSubmitting(true);
    try {
      await onSubmit(form);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6" noValidate>
      {formError && <Alert variant="error">{formError}</Alert>}

      {initial?.status === "REJECTED" && initial.review_note && (
        <Alert variant="error">
          Your KYC was not accepted: {initial.review_note}. Please correct it and
          resubmit.
        </Alert>
      )}

      <section className="space-y-4">
        <h3 className="font-display text-sm font-semibold uppercase tracking-wide text-muted">
          Personal details
        </h3>

        <Field label="Full name" htmlFor="full_name" error={errors.full_name} required>
          <Input
            id="full_name"
            value={values.full_name}
            onChange={(e) => set("full_name", e.target.value)}
            placeholder="Sita Sharma"
            disabled={submitting}
            aria-invalid={Boolean(errors.full_name)}
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Email" htmlFor="kyc_email" error={errors.email}>
            <Input
              id="kyc_email"
              type="email"
              value={values.email}
              onChange={(e) => set("email", e.target.value)}
              placeholder="sita@example.com"
              disabled={submitting}
            />
          </Field>
          <Field label="Phone" htmlFor="kyc_phone" error={errors.phone}>
            <Input
              id="kyc_phone"
              value={values.phone}
              onChange={(e) => set("phone", e.target.value)}
              placeholder="98XXXXXXXX"
              disabled={submitting}
            />
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Date of birth"
            htmlFor="date_of_birth"
            error={errors.date_of_birth}
          >
            <Input
              id="date_of_birth"
              type="date"
              value={values.date_of_birth}
              onChange={(e) => set("date_of_birth", e.target.value)}
              disabled={submitting}
            />
          </Field>
          <Field
            label="Marital status"
            htmlFor="marital_status"
            error={errors.marital_status}
          >
            <Select
              id="marital_status"
              value={values.marital_status}
              onChange={(e) =>
                set("marital_status", e.target.value as MaritalStatus | "")
              }
              disabled={submitting}
            >
              <option value="">Prefer not to say</option>
              {MARITAL_STATUSES.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <Field
          label="Family details"
          htmlFor="family_details"
          error={errors.family_details}
          hint="Spouse, parents or dependents relevant to this policy."
        >
          <Textarea
            id="family_details"
            value={values.family_details}
            onChange={(e) => set("family_details", e.target.value)}
            disabled={submitting}
          />
        </Field>
      </section>

      <section className="space-y-4">
        <h3 className="font-display text-sm font-semibold uppercase tracking-wide text-muted">
          Address
        </h3>
        <Field
          label="Permanent address"
          htmlFor="permanent_address"
          error={errors.permanent_address}
          required
        >
          <Textarea
            id="permanent_address"
            rows={2}
            value={values.permanent_address}
            onChange={(e) => set("permanent_address", e.target.value)}
            placeholder="Ward, municipality, district"
            disabled={submitting}
            aria-invalid={Boolean(errors.permanent_address)}
          />
        </Field>
        <Field
          label="Temporary address"
          htmlFor="temporary_address"
          error={errors.temporary_address}
          hint="Leave blank if same as permanent."
        >
          <Textarea
            id="temporary_address"
            rows={2}
            value={values.temporary_address}
            onChange={(e) => set("temporary_address", e.target.value)}
            disabled={submitting}
          />
        </Field>
      </section>

      <section className="space-y-4">
        <h3 className="font-display text-sm font-semibold uppercase tracking-wide text-muted">
          Identity document
        </h3>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Document type" htmlFor="document_type">
            <Select
              id="document_type"
              value={values.document_type}
              onChange={(e) => {
                set("document_type", e.target.value as DocumentType);
                // Clearing keeps the required-image logic honest on switch.
                setLocalErrors((old) => ({
                  ...old,
                  document_front: "",
                  document_back: "",
                }));
              }}
              disabled={submitting}
            >
              {DOCUMENT_TYPES.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            label="Document number"
            htmlFor="document_number"
            error={errors.document_number}
            required
          >
            <Input
              id="document_number"
              value={values.document_number}
              onChange={(e) => set("document_number", e.target.value)}
              disabled={submitting}
              aria-invalid={Boolean(errors.document_number)}
            />
          </Field>
        </div>

        <Field
          label={help.frontLabel}
          htmlFor="document_front"
          error={errors.document_front}
          required={!hasStoredFront}
          hint={
            hasStoredFront ? "A file is already on record. Upload to replace it." : undefined
          }
        >
          <FileInput
            id="document_front"
            onFile={setFront}
            disabled={submitting}
            invalid={Boolean(errors.document_front)}
          />
        </Field>

        {help.backLabel && (
          <Field
            label={help.backLabel}
            htmlFor="document_back"
            error={errors.document_back}
            required={help.backRequired && !initial?.document_back}
          >
            <FileInput
              id="document_back"
              onFile={setBack}
              disabled={submitting}
              invalid={Boolean(errors.document_back)}
            />
          </Field>
        )}
      </section>

      <div>
        <Button type="submit" loading={submitting} className="w-full sm:w-auto">
          {submitLabel}
        </Button>
        {footnote && <p className="mt-2 text-xs text-muted">{footnote}</p>}
      </div>
    </form>
  );
}
