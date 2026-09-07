/**
 * Trigger a browser download for an in-memory blob (e.g. a PDF fetched with an
 * `Authorization` header, which a plain `<a download>` link cannot carry).
 */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
