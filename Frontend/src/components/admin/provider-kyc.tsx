"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { Textarea } from "@/components/ui/textarea";
import { DownloadIcon, FileTextIcon } from "@/components/icons";
import {
  api,
  errorMessage,
  fieldErrors,
  type AdminProvider,
  type KycStatus,
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

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; documents: ProviderKycDocument[] };

/**
 * Admin dialog to review a provider organisation's verification paperwork: list
 * every uploaded document, download the file through the authenticated admin
 * route, and verify or reject each pending one with a note. Opened from a row in
 * {@link ProviderApprovals}. Documents may be PDFs, so files download rather than
 * preview inline.
 */
export function ProviderKycModal({
  provider,
  open,
  onClose,
}: {
  provider: AdminProvider;
  open: boolean;
  onClose: () => void;
}) {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    api.admin
      .listProviderKyc(authFetch, provider.id)
      .then((documents) => {
        if (!cancelled) setState({ phase: "ready", documents });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, provider.id, open]);

  function replace(updated: ProviderKycDocument) {
    setState((prev) =>
      prev.phase === "ready"
        ? {
            phase: "ready",
            documents: prev.documents.map((d) =>
              d.id === updated.id ? updated : d,
            ),
          }
        : prev,
    );
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`KYC — ${provider.company_name}`}
      className="max-w-2xl"
    >
      <div className="space-y-5">
        <p className="text-sm text-muted">
          Verification paperwork uploaded by{" "}
          <span className="font-medium text-ink">{provider.public_id}</span>.
          Download each file to review it, then verify or reject with a note the
          provider will see.
        </p>

        {state.phase === "loading" && (
          <div className="flex items-center justify-center py-10">
            <Spinner className="h-6 w-6 text-brand-500" />
          </div>
        )}

        {state.phase === "error" && (
          <Alert variant="error">
            We could not load these documents. Please close and try again.
          </Alert>
        )}

        {state.phase === "ready" && state.documents.length === 0 && (
          <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-10 text-center text-sm text-muted">
            This provider has not uploaded any KYC documents yet.
          </div>
        )}

        {state.phase === "ready" && state.documents.length > 0 && (
          <ul className="space-y-3">
            {state.documents.map((document) => (
              <ProviderKycRow
                key={document.id}
                provider={provider}
                document={document}
                onDecided={replace}
              />
            ))}
          </ul>
        )}
      </div>
    </Modal>
  );
}

function ProviderKycRow({
  provider,
  document,
  onDecided,
}: {
  provider: AdminProvider;
  document: ProviderKycDocument;
  onDecided: (updated: ProviderKycDocument) => void;
}) {
  const { authFetch } = useAuth();
  const [downloading, setDownloading] = useState(false);
  const [mode, setMode] = useState<"view" | "reject">("view");
  const [note, setNote] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [noteError, setNoteError] = useState("");

  const decided = document.status !== "PENDING";

  async function download() {
    setDownloading(true);
    setError("");
    try {
      const blob = await api.admin.providerKycDocument(
        authFetch,
        provider.id,
        document.id,
      );
      saveBlob(blob, document.file_name || `provider-kyc-${document.id}`);
    } catch (err) {
      setError(errorMessage(err, "Could not download this document."));
    } finally {
      setDownloading(false);
    }
  }

  async function verify() {
    setWorking(true);
    setError("");
    try {
      const updated = await api.admin.verifyProviderKyc(
        authFetch,
        provider.id,
        document.id,
      );
      onDecided(updated);
    } catch (err) {
      setError(errorMessage(err, "Could not verify this document."));
    } finally {
      setWorking(false);
    }
  }

  async function reject() {
    setWorking(true);
    setError("");
    setNoteError("");
    try {
      const updated = await api.admin.rejectProviderKyc(
        authFetch,
        provider.id,
        document.id,
        note.trim(),
      );
      onDecided(updated);
      setMode("view");
    } catch (err) {
      setNoteError(fieldErrors(err).note ?? "");
      setError(errorMessage(err, "Could not reject this document."));
    } finally {
      setWorking(false);
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
        </div>
      </div>

      {document.status === "REJECTED" && document.review_note && (
        <Alert variant="info" className="mt-3">
          <span className="font-medium">Review note:</span> {document.review_note}
        </Alert>
      )}

      {error && (
        <Alert variant="error" className="mt-3">
          {error}
        </Alert>
      )}

      {mode === "reject" ? (
        <div className="mt-3 space-y-3">
          <Field
            label="Reason for rejection"
            htmlFor={`reject-note-${document.id}`}
            error={noteError}
          >
            <Textarea
              id={`reject-note-${document.id}`}
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Tell the provider what to fix and re-upload."
              disabled={working}
            />
          </Field>
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setMode("view")}
              disabled={working}
            >
              Back
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={reject}
              loading={working}
              disabled={!note.trim()}
            >
              Confirm rejection
            </Button>
          </div>
        </div>
      ) : (
        !decided && (
          <div className="mt-3 flex justify-end gap-2 border-t border-line pt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setMode("reject")}
              disabled={working}
            >
              Reject
            </Button>
            <Button
              variant="success"
              size="sm"
              onClick={verify}
              loading={working}
            >
              Verify
            </Button>
          </div>
        )
      )}
    </li>
  );
}
