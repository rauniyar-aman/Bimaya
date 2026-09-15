"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

/** Default accepted image types and the ceiling enforced client-side. */
const DEFAULT_ACCEPT = ["image/jpeg", "image/png", "image/webp"];
const DEFAULT_MAX_BYTES = 5 * 1024 * 1024; // 5 MB

/** Short human labels for the MIME types we accept, for placeholder/error copy. */
const TYPE_LABELS: Record<string, string> = {
  "image/jpeg": "JPG",
  "image/png": "PNG",
  "image/webp": "WebP",
  "application/pdf": "PDF",
};

/** "JPG, PNG or WebP" — an Oxford-free "or" list of the accepted type labels. */
function describeTypes(types: string[]): string {
  const names = types.map((t) => TYPE_LABELS[t] ?? t);
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} or ${names[names.length - 1]}`;
}

function describeSize(maxBytes: number): string {
  return `${Math.round(maxBytes / (1024 * 1024))} MB`;
}

interface FileInputProps {
  id: string;
  /** Called with the chosen file, or `null` when cleared or rejected. */
  onFile: (file: File | null) => void;
  disabled?: boolean;
  /** Invalid styling driven from the parent form. */
  invalid?: boolean;
  /** MIME types to accept. Defaults to the image trio (JPG/PNG/WebP). */
  accept?: string[];
  /** Size ceiling in bytes. Defaults to 5 MB. */
  maxBytes?: number;
}

/**
 * A single-file picker with a live preview and client-side type/size checks.
 * It doesn't own form state — the parent decides what to do with the file — but
 * it guards against obviously bad uploads before they reach the API. Images get
 * a thumbnail preview; other allowed types (e.g. PDF) show a document chip.
 */
export function FileInput({
  id,
  onFile,
  disabled,
  invalid,
  accept = DEFAULT_ACCEPT,
  maxBytes = DEFAULT_MAX_BYTES,
}: FileInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [name, setName] = useState<string | null>(null);
  const [localError, setLocalError] = useState("");

  const imagesOnly = accept.every((t) => t.startsWith("image/"));
  const typeLabel = describeTypes(accept);
  const sizeLabel = describeSize(maxBytes);

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setLocalError("");

    if (!file) {
      reset();
      return;
    }
    if (!accept.includes(file.type)) {
      setLocalError(
        `Please choose a ${typeLabel} ${imagesOnly ? "image" : "file"}.`,
      );
      resetInput();
      onFile(null);
      return;
    }
    if (file.size > maxBytes) {
      setLocalError(
        `That ${imagesOnly ? "image" : "file"} is over ${sizeLabel}. Please choose a smaller file.`,
      );
      resetInput();
      onFile(null);
      return;
    }

    // Only images get an object-URL thumbnail; other types show a doc chip.
    const isImage = file.type.startsWith("image/");
    setName(file.name);
    setPreview((old) => {
      if (old) URL.revokeObjectURL(old);
      return isImage ? URL.createObjectURL(file) : null;
    });
    onFile(file);
  }

  function resetInput() {
    if (inputRef.current) inputRef.current.value = "";
    setPreview((old) => {
      if (old) URL.revokeObjectURL(old);
      return null;
    });
    setName(null);
  }

  function reset() {
    resetInput();
    setLocalError("");
    onFile(null);
  }

  return (
    <div className="space-y-2">
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept={accept.join(",")}
        onChange={handleChange}
        disabled={disabled}
        className="sr-only"
      />

      <div
        className={cn(
          "flex items-center gap-3 rounded-lg border border-dashed p-3",
          invalid ? "border-danger-border bg-danger-surface/40" : "border-line bg-surface/40",
        )}
      >
        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={preview}
            alt="Selected document preview"
            className="h-14 w-14 shrink-0 rounded-md border border-line object-cover"
          />
        ) : name ? (
          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-md border border-line bg-card text-brand-500">
            <DocumentIcon className="h-6 w-6" />
          </span>
        ) : (
          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-md border border-line bg-card text-xs text-muted">
            No file
          </span>
        )}

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm text-ink">
            {name ?? `${typeLabel} · up to ${sizeLabel}`}
          </p>
          <div className="mt-1.5 flex gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={disabled}
              onClick={() => inputRef.current?.click()}
            >
              {name ? "Change" : imagesOnly ? "Choose image" : "Choose file"}
            </Button>
            {name && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={disabled}
                onClick={reset}
              >
                Remove
              </Button>
            )}
          </div>
        </div>
      </div>

      {localError && (
        <p role="alert" className="text-sm text-danger">
          {localError}
        </p>
      )}
    </div>
  );
}

function DocumentIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5" />
    </svg>
  );
}
