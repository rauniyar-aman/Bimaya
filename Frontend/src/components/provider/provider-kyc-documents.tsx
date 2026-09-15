"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { useProviderPortal } from "@/components/provider/provider-portal";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { FileInput } from "@/components/ui/file-input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { DownloadIcon, FileTextIcon } from "@/components/icons";
import {
  api,
  errorMessage,
  fieldErrors,
  type KycStatus,
  type ProviderKycDocType,
  type ProviderKycDocument,
} from "@/lib/api";
import { formatDate } from "@/lib/date";
import { saveBlob } from "@/lib/download";

/** Status → pill styling; the human label comes from the server `status_display`. */
const STATUS_VARIANT: Record<KycStatus, "active" | "pending" | "failed"> = {
  PENDING: "pending",
  VERIFIED: "active",
  REJECTED: "failed",
};

/** The document kinds a provider can file, for the upload picker. */
const DOC_TYPES: { value: ProviderKycDocType; label: string }[] = [
  { value: "REGISTRATION", label: "Company registration" },
  { value: "TAX", label: "Tax / PAN certificate" },
  { value: "LICENSE", label: "Insurance licence" },
  { value: "OTHER", label: "Other supporting document" },
];

const ACCEPT = ["application/pdf", "image/jpeg", "image/png", "image/webp"];
const MAX_BYTES = 10 * 1024 * 1024; // 10 MB

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; documents: ProviderKycDocument[] };

/**
 * The provider portal's KYC document area: upload company paperwork
 * (registration / tax / licence), track each document's review status, download
 * a copy, and remove one that is still pending. Gated by the caller's org
 * permissions (`provider_kyc.view` / `provider_kyc.upload`); the files
 * themselves stream only through the authenticated, org-scoped download route.
 */
export function ProviderKycDocuments() {
  const { authFetch } = useAuth();
  const { permissions } = useProviderPortal();
  const canView = permissions.includes("provider_kyc.view");
  const canUpload = permissions.includes("provider_kyc.upload");

  const [state, setState] = useState<State>({ phase: "loading" });
  const [removing, setRemoving] = useState<ProviderKycDocument | null>(null);

  useEffect(() => {
    if (!canView) return;
    let cancelled = false;
    api.provider
      .listKyc(authFetch)
      .then((documents) => {
        if (!cancelled) setState({ phase: "ready", documents });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, canView]);

  function prepend(document: ProviderKycDocument) {
    setState((prev) =>
      prev.phase === "ready"
        ? { phase: "ready", documents: [document, ...prev.documents] }
        : prev,
    );
  }

  function drop(id: number) {
    setState((prev) =>
      prev.phase === "ready"
        ? { phase: "ready", documents: prev.documents.filter((d) => d.id !== id) }
        : prev,
    );
  }

  if (!canView) {
    return (
      <Alert variant="error">
        You do not have access to this organisation&rsquo;s KYC documents.
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-xl font-semibold text-ink sm:text-2xl">
          KYC documents
        </h1>
        <p className="mt-1 text-sm text-muted">
          Upload your company&rsquo;s registration, tax and licence paperwork. Our
          team reviews each document before your organisation is approved to sell.
        </p>
      </header>

      {canUpload && <UploadCard onUploaded={prepend} />}

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error">
          We could not load your documents. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.documents.length === 0 && (
        <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center text-sm text-muted">
          No documents uploaded yet.
          {canUpload
            ? " Add your company paperwork above to start verification."
            : ""}
        </div>
      )}

      {state.phase === "ready" && state.documents.length > 0 && (
        <ul className="space-y-3">
          {state.documents.map((document) => (
            <DocumentRow
              key={document.id}
              document={document}
              canUpload={canUpload}
              onRemove={() => setRemoving(document)}
            />
          ))}
        </ul>
      )}

      <RemoveModal
        document={removing}
        onClose={() => setRemoving(null)}
        onRemoved={(id) => {
          drop(id);
          setRemoving(null);
        }}
      />
    </div>
  );
}

function DocumentRow({
  document,
  canUpload,
  onRemove,
}: {
  document: ProviderKycDocument;
  canUpload: boolean;
  onRemove: () => void;
}) {
  const { authFetch } = useAuth();
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  async function download() {
    setDownloading(true);
    setError("");
    try {
      const blob = await api.provider.downloadKyc(authFetch, document.id);
      saveBlob(blob, document.file_name || `provider-kyc-${document.id}`);
    } catch (err) {
      setError(errorMessage(err, "Could not download this document."));
    } finally {
      setDownloading(false);
    }
  }

  return (
    <li className="rounded-2xl border border-line bg-card p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
            <FileTextIcon className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <p className="font-medium text-ink">{document.document_type_display}</p>
            <p className="truncate text-xs text-muted">{document.file_name}</p>
            <p className="mt-1 text-xs text-muted">
              Uploaded {formatDate(document.created_at)}
              {document.uploaded_by_email ? ` · ${document.uploaded_by_email}` : ""}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <StatusPill status={STATUS_VARIANT[document.status]}>
            {document.status_display}
          </StatusPill>
          <Button
            variant="secondary"
            size="sm"
            onClick={download}
            loading={downloading}
          >
            <DownloadIcon className="h-4 w-4" />
            Download
          </Button>
          {canUpload && document.status === "PENDING" && (
            <Button variant="ghost" size="sm" onClick={onRemove}>
              Remove
            </Button>
          )}
        </div>
      </div>

      {document.status === "REJECTED" && document.review_note && (
        <Alert variant="error" className="mt-3">
          <span className="font-medium">Review note:</span> {document.review_note}
        </Alert>
      )}
      {error && (
        <Alert variant="error" className="mt-3">
          {error}
        </Alert>
      )}
    </li>
  );
}

function UploadCard({
  onUploaded,
}: {
  onUploaded: (document: ProviderKycDocument) => void;
}) {
  const { authFetch } = useAuth();
  const [docType, setDocType] = useState<ProviderKycDocType>("REGISTRATION");
  const [file, setFile] = useState<File | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [uploading, setUploading] = useState(false);
  // Remount the file input after a successful upload to clear its preview.
  const [inputSeq, setInputSeq] = useState(0);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");
    if (!file) {
      setErrors({ file: "Choose a file to upload." });
      return;
    }
    setUploading(true);
    try {
      const form = new FormData();
      form.set("document_type", docType);
      form.set("file", file);
      const document = await api.provider.uploadKyc(authFetch, form);
      onUploaded(document);
      setFile(null);
      setDocType("REGISTRATION");
      setInputSeq((s) => s + 1);
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(errorMessage(error, "Could not upload this document."));
    } finally {
      setUploading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload a document</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {formError && <Alert variant="error">{formError}</Alert>}

          <Field label="Document type" htmlFor="doc_type" error={errors.document_type}>
            <Select
              id="doc_type"
              value={docType}
              onChange={(e) => setDocType(e.target.value as ProviderKycDocType)}
              className="sm:max-w-sm"
            >
              {DOC_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </Select>
          </Field>

          <Field
            label="File"
            htmlFor="doc_file"
            error={errors.file}
            hint="PDF or image, up to 10 MB."
            required
          >
            <FileInput
              key={inputSeq}
              id="doc_file"
              accept={ACCEPT}
              maxBytes={MAX_BYTES}
              onFile={setFile}
              disabled={uploading}
              invalid={Boolean(errors.file)}
            />
          </Field>

          <Button type="submit" loading={uploading}>
            Upload document
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function RemoveModal({
  document,
  onClose,
  onRemoved,
}: {
  document: ProviderKycDocument | null;
  onClose: () => void;
  onRemoved: (id: number) => void;
}) {
  const { authFetch } = useAuth();
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  async function confirm() {
    if (!document) return;
    setWorking(true);
    setError("");
    try {
      await api.provider.deleteKyc(authFetch, document.id);
      onRemoved(document.id);
    } catch (err) {
      setError(errorMessage(err, "Could not remove this document."));
    } finally {
      setWorking(false);
    }
  }

  return (
    <Modal
      open={document !== null}
      onClose={() => (working ? undefined : onClose())}
      title="Remove document"
    >
      {document && (
        <div className="space-y-4">
          <p className="text-sm text-muted">
            Remove{" "}
            <strong className="text-ink">{document.document_type_display}</strong>{" "}
            ({document.file_name})? You can upload it again if you need to.
          </p>
          {error && <Alert variant="error">{error}</Alert>}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose} disabled={working}>
              Cancel
            </Button>
            <Button variant="primary" onClick={confirm} loading={working}>
              Remove
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
