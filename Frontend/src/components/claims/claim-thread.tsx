"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, errorMessage, type Claim, type UserRole } from "@/lib/api";
import { formatRelativeTime } from "@/lib/date";
import { cn } from "@/lib/cn";

/** Which party is viewing the thread (drives alignment and the post endpoint). */
type Side = "customer" | "provider";

const SIDE_ROLE: Record<Side, UserRole> = {
  customer: "CUSTOMER",
  provider: "PROVIDER",
};

/** Human label for a message author, from the current viewer's perspective. */
function authorLabel(role: UserRole, mine: boolean): string {
  if (mine) return "You";
  if (role === "PROVIDER") return "Insurer";
  if (role === "CUSTOMER") return "Customer";
  return "Bimaya";
}

/**
 * The customer↔insurer message thread on a claim. Renders the messages chat-style
 * (the viewer's own on the right) and a composer that posts through the endpoint
 * for the given `side`, handing the refreshed claim back via `onUpdated`.
 */
export function ClaimThread({
  claim,
  side,
  readOnly = false,
  onUpdated,
}: {
  claim: Claim;
  side: Side;
  /** When true, the thread is shown but the composer is hidden (e.g. viewers). */
  readOnly?: boolean;
  onUpdated: (claim: Claim) => void;
}) {
  const { authFetch } = useAuth();
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const myRole = SIDE_ROLE[side];
  const otherLabel = side === "customer" ? "the insurer" : "the customer";

  async function handleSend(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = body.trim();
    if (!trimmed) return;
    setSending(true);
    setError("");
    try {
      const updated =
        side === "customer"
          ? await api.claims.postMessage(authFetch, claim.id, trimmed)
          : await api.provider.postClaimMessage(authFetch, claim.id, trimmed);
      onUpdated(updated);
      setBody("");
    } catch (err) {
      setError(errorMessage(err, "Could not send your message. Please try again."));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-display text-lg font-semibold text-ink">Messages</h2>
        {!readOnly && (
          <p className="mt-1 text-sm text-muted">
            Send a message to {otherLabel} about this claim.
          </p>
        )}
      </div>

      {claim.messages.length === 0 ? (
        <p className="rounded-lg border border-dashed border-line bg-surface/50 px-4 py-6 text-center text-sm text-muted">
          No messages yet.
        </p>
      ) : (
        <ul className="max-h-80 space-y-3 overflow-y-auto pr-1">
          {claim.messages.map((message) => {
            const mine = message.author_role === myRole;
            return (
              <li
                key={message.id}
                className={cn("flex", mine ? "justify-end" : "justify-start")}
              >
                <div className="max-w-[80%]">
                  <div
                    className={cn(
                      "text-xs text-muted",
                      mine ? "text-right" : "text-left",
                    )}
                  >
                    {authorLabel(message.author_role, mine)}
                    {" · "}
                    {formatRelativeTime(message.created_at)}
                  </div>
                  <div
                    className={cn(
                      "mt-1 whitespace-pre-line rounded-2xl px-3.5 py-2 text-sm",
                      mine
                        ? "bg-brand-500 text-white"
                        : "border border-line bg-surface text-ink",
                    )}
                  >
                    {message.body}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {error && <Alert variant="error">{error}</Alert>}

      {!readOnly && (
        <form onSubmit={handleSend} className="space-y-2">
          <Textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={3}
            placeholder="Write a message…"
            disabled={sending}
            aria-label="Message"
          />
          <div className="flex justify-end">
            <Button type="submit" size="sm" loading={sending} disabled={!body.trim()}>
              Send message
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
