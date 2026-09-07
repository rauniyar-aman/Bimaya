"use client";

import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { FileInput } from "@/components/ui/file-input";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

/** Claim documents may be photos or PDFs (bills, medical/police reports). */
const CLAIM_ACCEPT = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/pdf",
];
const CLAIM_MAX_BYTES = 10 * 1024 * 1024; // 10 MB

interface DocRow {
  key: number;
  file: File | null;
}

export interface ClaimFormProps {
  /** The ACTIVE purchase this claim is filed against. */
  purchaseId: number;
  /** Called with a built FormData once client-side checks pass. */
  onSubmit: (form: FormData) => Promise<void>;
  /** Field errors from the API (server-side validation). */
  fieldErrors?: Record<string, string>;
  /** Top-level error message from the API. */
  formError?: string;
  /** Cover start date, used to bound the incident-date picker when known. */
  minDate?: string | null;
  submitLabel?: string;
}

/**
 * Collects an insurance claim: incident details, the amount claimed and one or
 * more supporting documents. Building the multipart payload lives here so the
 * create page can stay focused on choosing which policy the claim is against.
 */
export function ClaimForm({
  purchaseId,
  onSubmit,
  fieldErrors = {},
  formError,
  minDate,
  submitLabel = "Submit claim",
}: ClaimFormProps) {
  const today = new Date().toISOString().slice(0, 10);
  const [values, setValues] = useState({
    incident_date: "",
    incident_location: "",
    description: "",
    claimed_amount: "",
  });
  const [docs, setDocs] = useState<DocRow[]>([{ key: 0, file: null }]);
  const [nextKey, setNextKey] = useState(1);
  const [localErrors, setLocalErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const errors = { ...fieldErrors, ...localErrors };

  function set<K extends keyof typeof values>(key: K, value: string) {
    setValues((v) => ({ ...v, [key]: value }));
  }

  function setFile(key: number, file: File | null) {
    setDocs((rows) => rows.map((r) => (r.key === key ? { ...r, file } : r)));
  }

  function addRow() {
    setDocs((rows) => [...rows, { key: nextKey, file: null }]);
    setNextKey((k) => k + 1);
  }

  function removeRow(key: number) {
    setDocs((rows) =>
      rows.length === 1 ? rows : rows.filter((r) => r.key !== key),
    );
  }

  function validate(files: File[]): boolean {
    const next: Record<string, string> = {};
    if (!values.incident_date) next.incident_date = "Tell us when the incident happened.";
    if (!values.description.trim())
      next.description = "Describe what happened so the insurer can assess it.";
    const amount = Number(values.claimed_amount);
    if (!values.claimed_amount.trim() || !Number.isFinite(amount) || amount <= 0)
      next.claimed_amount = "Enter the amount you are claiming.";
    if (files.length === 0)
      next.documents = "Attach at least one supporting document.";
    setLocalErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const files = docs.map((r) => r.file).filter((f): f is File => f !== null);
    if (!validate(files)) return;

    const form = new FormData();
    form.set("purchase", String(purchaseId));
    form.set("incident_date", values.incident_date);
    form.set("incident_location", values.incident_location.trim());
    form.set("description", values.description.trim());
    form.set("claimed_amount", values.claimed_amount.trim());
    for (const file of files) form.append("documents", file);

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

      <section className="space-y-4">
        <h3 className="font-display text-sm font-semibold uppercase tracking-wide text-muted">
          Incident details
        </h3>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Date of incident"
            htmlFor="incident_date"
            error={errors.incident_date}
            required
          >
            <Input
              id="incident_date"
              type="date"
              min={minDate ?? undefined}
              max={today}
              value={values.incident_date}
              onChange={(e) => set("incident_date", e.target.value)}
              disabled={submitting}
              aria-invalid={Boolean(errors.incident_date)}
            />
          </Field>
          <Field
            label="Where it happened"
            htmlFor="incident_location"
            error={errors.incident_location}
            hint="Optional — city, road or place."
          >
            <Input
              id="incident_location"
              value={values.incident_location}
              onChange={(e) => set("incident_location", e.target.value)}
              placeholder="e.g. Kalanki, Kathmandu"
              disabled={submitting}
            />
          </Field>
        </div>

        <Field
          label="What happened"
          htmlFor="description"
          error={errors.description}
          hint="Describe the loss or event and any parties involved."
          required
        >
          <Textarea
            id="description"
            rows={4}
            value={values.description}
            onChange={(e) => set("description", e.target.value)}
            disabled={submitting}
            aria-invalid={Boolean(errors.description)}
          />
        </Field>

        <Field
          label="Amount claimed (Rs)"
          htmlFor="claimed_amount"
          error={errors.claimed_amount}
          hint="The total you are claiming, in rupees."
          required
        >
          <Input
            id="claimed_amount"
            inputMode="decimal"
            value={values.claimed_amount}
            onChange={(e) => set("claimed_amount", e.target.value)}
            placeholder="e.g. 50000"
            disabled={submitting}
            aria-invalid={Boolean(errors.claimed_amount)}
          />
        </Field>
      </section>

      <section className="space-y-4">
        <div>
          <h3 className="font-display text-sm font-semibold uppercase tracking-wide text-muted">
            Supporting documents
          </h3>
          <p className="mt-1 text-sm text-muted">
            Bills, medical or police reports, and photos. JPG, PNG, WebP or PDF.
          </p>
        </div>

        {errors.documents && <Alert variant="error">{errors.documents}</Alert>}

        <div className="space-y-3">
          {docs.map((row, index) => (
            <div key={row.key}>
              <div className="mb-1.5 flex items-center justify-between">
                <span className="text-sm font-medium text-ink">
                  Document {index + 1}
                </span>
                {docs.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeRow(row.key)}
                    disabled={submitting}
                    className="text-sm font-medium text-muted underline-offset-4 hover:text-red-600 hover:underline disabled:opacity-60"
                  >
                    Remove
                  </button>
                )}
              </div>
              <FileInput
                id={`claim_doc_${row.key}`}
                onFile={(file) => setFile(row.key, file)}
                disabled={submitting}
                accept={CLAIM_ACCEPT}
                maxBytes={CLAIM_MAX_BYTES}
              />
            </div>
          ))}
        </div>

        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={addRow}
          disabled={submitting}
        >
          + Add another document
        </Button>
      </section>

      <div>
        <Button type="submit" loading={submitting} className="w-full sm:w-auto">
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
