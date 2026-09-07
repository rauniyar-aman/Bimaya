"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { saveBlob } from "@/lib/download";
import { api, errorMessage, type ClaimDocument } from "@/lib/api";

/** Extension by MIME type, so a downloaded document keeps a sensible name. */
const EXT_BY_TYPE: Record<string, string> = {
  "application/pdf": "pdf",
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
};

/**
 * The supporting documents on a claim, each downloaded through the authenticated
 * owner-or-underwriter endpoint (never a raw media URL — these are sensitive
 * medical/police/financial files). Shared by the customer detail page and the
 * provider review queue, since both parties may read the same files.
 */
export function ClaimDocumentList({
  claimId,
  documents,
  emptyText = "No documents attached.",
}: {
  claimId: number;
  documents: ClaimDocument[];
  emptyText?: string;
}) {
  const { authFetch } = useAuth();
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [error, setError] = useState("");

  async function download(doc: ClaimDocument) {
    setError("");
    setDownloadingId(doc.id);
    try {
      const blob = await api.claims.document(authFetch, claimId, doc.id);
      const ext = EXT_BY_TYPE[blob.type];
      const base = `Bimaya-Claim-${claimId}-document-${doc.id}`;
      saveBlob(blob, ext ? `${base}.${ext}` : base);
    } catch (err) {
      setError(errorMessage(err, "Could not download that document."));
    } finally {
      setDownloadingId(null);
    }
  }

  if (documents.length === 0) {
    return <p className="text-sm text-muted">{emptyText}</p>;
  }

  return (
    <div className="space-y-3">
      {error && <Alert variant="error">{error}</Alert>}
      <ul className="divide-y divide-line rounded-lg border border-line">
        {documents.map((doc, index) => (
          <li
            key={doc.id}
            className="flex items-center justify-between gap-3 px-4 py-3"
          >
            <span className="min-w-0 truncate text-sm text-ink">
              {doc.caption || `Document ${index + 1}`}
            </span>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => download(doc)}
              loading={downloadingId === doc.id}
              disabled={downloadingId !== null}
            >
              Download
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
