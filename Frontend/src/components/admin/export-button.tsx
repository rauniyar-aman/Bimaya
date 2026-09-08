"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { DownloadIcon } from "@/components/icons";
import { saveBlob } from "@/lib/download";
import { errorMessage } from "@/lib/api";

interface ExportButtonProps {
  /** Fetches the report as a CSV blob (usually an `api.admin.export*` call). */
  onExport: () => Promise<Blob>;
  /** Filename for the download; the server also sets one via Content-Disposition. */
  filename: string;
  label?: string;
}

/**
 * Downloads a CSV report for the current admin view. The export honours the
 * table's active filters and search because the caller passes them through to
 * `onExport`, so the file matches what's on screen.
 */
export function ExportButton({ onExport, filename, label = "Export CSV" }: ExportButtonProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setBusy(true);
    setError("");
    try {
      const blob = await onExport();
      saveBlob(blob, filename);
    } catch (err) {
      setError(errorMessage(err, "Could not export. Please try again."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative">
      <Button variant="secondary" size="sm" onClick={run} loading={busy}>
        {!busy && <DownloadIcon className="h-4 w-4" />}
        {label}
      </Button>
      {error && (
        <p
          role="alert"
          className="absolute right-0 top-full z-10 mt-1 whitespace-nowrap text-xs text-red-600"
        >
          {error}
        </p>
      )}
    </div>
  );
}
