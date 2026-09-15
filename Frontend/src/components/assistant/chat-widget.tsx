"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { ChatIcon, XIcon } from "@/components/icons";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, errorCode, errorMessage, type ChatTurn } from "@/lib/api";
import { cn } from "@/lib/cn";

/** A short-lived error the composer surfaces below the thread. */
type ChatError = { variant: "info" | "error"; message: string };

const DISABLED_MESSAGE =
  "The AI advisor isn't switched on just yet — it's coming soon. In the meantime, try the plan finder above.";

/**
 * Floating insurance Q&A assistant, shown on every page for signed-in users.
 * History lives only in this component's state (never persisted) and the reply
 * comes from the flag-gated backend — when the advisor is off, the composer
 * shows a friendly "coming soon" note instead of failing.
 */
export function ChatWidget() {
  const { isAuthenticated, authFetch } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<ChatError | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  // Keep the newest message in view as the thread grows.
  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, open, sending]);

  // Never render for signed-out visitors (the endpoint needs a session).
  if (!isAuthenticated) return null;

  async function handleSend(event: React.FormEvent) {
    event.preventDefault();
    const message = input.trim();
    if (!message || sending) return;

    const history = messages;
    setMessages([...history, { role: "user", content: message }]);
    setInput("");
    setError(null);
    setSending(true);
    try {
      const { reply } = await api.assistant.chat(authFetch, {
        message,
        history,
      });
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch (err) {
      const code = errorCode(err);
      if (code === "assistant_disabled") {
        setError({ variant: "info", message: DISABLED_MESSAGE });
      } else if (code === "assistant_unavailable") {
        setError({
          variant: "error",
          message:
            "The advisor is unavailable right now. Please try again in a moment.",
        });
      } else {
        setError({
          variant: "error",
          message: errorMessage(err, "Could not send your message. Please try again."),
        });
      }
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends; Shift+Enter inserts a newline (standard chat behaviour).
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend(event as unknown as React.FormEvent);
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end sm:bottom-8 sm:right-8">
      {open && (
        <div className="mb-3 flex h-[30rem] w-[calc(100vw-2rem)] max-w-sm flex-col overflow-hidden rounded-2xl border border-line bg-card shadow-xl">
          <header className="flex items-center justify-between gap-2 border-b border-line bg-brand-500 px-4 py-3 text-white">
            <div>
              <p className="font-display text-sm font-semibold">Bimaya advisor</p>
              <p className="text-xs text-white/80">Ask about insurance in Nepal</p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close advisor"
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-white/90 transition-colors hover:bg-white/15"
            >
              <XIcon className="h-4 w-4" />
            </button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {messages.length === 0 ? (
              <div className="rounded-2xl border border-line bg-surface px-3.5 py-2.5 text-sm text-ink">
                Hi! I can explain insurance terms and help you understand the plans
                on Bimaya. What would you like to know?
              </div>
            ) : (
              messages.map((turn, i) => {
                const mine = turn.role === "user";
                return (
                  <div
                    key={i}
                    className={cn("flex", mine ? "justify-end" : "justify-start")}
                  >
                    <div
                      className={cn(
                        "max-w-[85%] whitespace-pre-line rounded-2xl px-3.5 py-2 text-sm",
                        mine
                          ? "bg-brand-500 text-white"
                          : "border border-line bg-surface text-ink",
                      )}
                    >
                      {turn.content}
                    </div>
                  </div>
                );
              })
            )}

            {error && <Alert variant={error.variant}>{error.message}</Alert>}

            <div ref={endRef} />
          </div>

          <form
            onSubmit={handleSend}
            className="space-y-2 border-t border-line px-4 py-3"
          >
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              placeholder="Ask a question…"
              disabled={sending}
              aria-label="Message the advisor"
            />
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs text-muted">
                Don&apos;t share ID or health numbers.
              </p>
              <Button
                type="submit"
                size="sm"
                loading={sending}
                disabled={!input.trim()}
              >
                Send
              </Button>
            </div>
          </form>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close advisor" : "Open AI advisor"}
        aria-expanded={open}
        className="inline-flex h-14 w-14 items-center justify-center rounded-full bg-brand-500 text-white shadow-lg transition-colors hover:bg-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
      >
        {open ? (
          <XIcon className="h-6 w-6" />
        ) : (
          <ChatIcon className="h-6 w-6" />
        )}
      </button>
    </div>
  );
}
