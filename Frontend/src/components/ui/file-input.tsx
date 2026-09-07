"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

/** Accepted image types and the ceiling we enforce client-side before upload. */
const ACCEPTED = ["image/jpeg", "image/png", "image/webp"];
const MAX_BYTES = 5 * 1024 * 1024; // 5 MB

interface FileInputProps {
  id: string;
  /** Called with the chosen file, or `null` when cleared or rejected. */
  onFile: (file: File | null) => void;
  disabled?: boolean;
  /** Invalid styling driven from the parent form. */
  invalid?: boolean;
}

/**
 * A single-image picker with a live preview and client-side type/size checks.
 * It doesn't own form state — the parent decides what to do with the file — but
 * it does guard against obviously bad uploads before they reach the API.
 */
export function FileInput({ id, onFile, disabled, invalid }: FileInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [name, setName] = useState<string | null>(null);
  const [localError, setLocalError] = useState("");

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setLocalError("");

    if (!file) {
      reset();
      return;
    }
    if (!ACCEPTED.includes(file.type)) {
      setLocalError("Please choose a JPG, PNG or WebP image.");
      resetInput();
      onFile(null);
      return;
    }
    if (file.size > MAX_BYTES) {
      setLocalError("That image is over 5 MB. Please choose a smaller file.");
      resetInput();
      onFile(null);
      return;
    }

    setName(file.name);
    setPreview((old) => {
      if (old) URL.revokeObjectURL(old);
      return URL.createObjectURL(file);
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
        accept={ACCEPTED.join(",")}
        onChange={handleChange}
        disabled={disabled}
        className="sr-only"
      />

      <div
        className={cn(
          "flex items-center gap-3 rounded-lg border border-dashed p-3",
          invalid ? "border-red-300 bg-red-50/40" : "border-line bg-surface/40",
        )}
      >
        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={preview}
            alt="Selected document preview"
            className="h-14 w-14 shrink-0 rounded-md border border-line object-cover"
          />
        ) : (
          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-md border border-line bg-white text-xs text-muted">
            No file
          </span>
        )}

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm text-ink">
            {name ?? "JPG, PNG or WebP · up to 5 MB"}
          </p>
          <div className="mt-1.5 flex gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={disabled}
              onClick={() => inputRef.current?.click()}
            >
              {name ? "Change" : "Choose image"}
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
        <p role="alert" className="text-sm text-red-600">
          {localError}
        </p>
      )}
    </div>
  );
}
