"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { NotificationRow } from "@/components/notifications/notification-row";
import { Spinner } from "@/components/ui/spinner";
import { api, type AppNotification } from "@/lib/api";

interface NotificationPanelProps {
  onClose: () => void;
  /** Keeps the bell badge in sync as rows are read here. */
  onCountChange: (count: number) => void;
}

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; items: AppNotification[] };

/** Dropdown feed of the most recent notifications, anchored under the bell. */
export function NotificationPanel({
  onClose,
  onCountChange,
}: NotificationPanelProps) {
  const { authFetch } = useAuth();
  const router = useRouter();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [marking, setMarking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.notifications
      .list(authFetch)
      .then((page) => {
        if (!cancelled) setState({ phase: "ready", items: page.results });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch]);

  function unreadCount(items: AppNotification[]) {
    return items.filter((n) => !n.is_read).length;
  }

  async function handleActivate(notification: AppNotification) {
    if (!notification.is_read) {
      // Optimistically flip the row so the panel feels instant.
      setState((prev) => {
        if (prev.phase !== "ready") return prev;
        const items = prev.items.map((n) =>
          n.id === notification.id ? { ...n, is_read: true } : n,
        );
        onCountChange(unreadCount(items));
        return { phase: "ready", items };
      });
      api.notifications.markRead(authFetch, notification.id).catch(() => {
        // Best-effort; the next poll will reconcile the true state.
      });
    }
    onClose();
    if (notification.url) router.push(notification.url);
  }

  async function handleMarkAll() {
    setMarking(true);
    try {
      await api.notifications.markAllRead(authFetch);
      setState((prev) => {
        if (prev.phase !== "ready") return prev;
        return {
          phase: "ready",
          items: prev.items.map((n) => ({ ...n, is_read: true })),
        };
      });
      onCountChange(0);
    } catch {
      // Leave the rows as-is; the periodic poll will catch up.
    } finally {
      setMarking(false);
    }
  }

  const hasUnread =
    state.phase === "ready" && state.items.some((n) => !n.is_read);

  return (
    <div
      role="menu"
      className="absolute right-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-xl border border-line bg-card shadow-lg sm:w-96"
    >
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <p className="text-sm font-semibold text-ink">Notifications</p>
        {hasUnread && (
          <button
            type="button"
            onClick={handleMarkAll}
            disabled={marking}
            className="text-xs font-medium text-brand-ink transition-colors hover:text-brand-700 disabled:opacity-60 dark:hover:text-brand-200"
          >
            {marking ? "Marking…" : "Mark all read"}
          </button>
        )}
      </div>

      <div className="max-h-96 overflow-y-auto p-1.5">
        {state.phase === "loading" && (
          <div className="flex items-center justify-center py-10">
            <Spinner className="h-5 w-5 text-brand-500" />
          </div>
        )}

        {state.phase === "error" && (
          <p className="px-3 py-8 text-center text-sm text-muted">
            We could not load your notifications.
          </p>
        )}

        {state.phase === "ready" && state.items.length === 0 && (
          <p className="px-3 py-10 text-center text-sm text-muted">
            You are all caught up.
          </p>
        )}

        {state.phase === "ready" &&
          state.items.map((notification) => (
            <NotificationRow
              key={notification.id}
              notification={notification}
              onActivate={handleActivate}
              compact
            />
          ))}
      </div>

      <div className="border-t border-line p-1.5">
        <Link
          href="/dashboard/notifications"
          onClick={onClose}
          role="menuitem"
          className="block rounded-lg px-3 py-2 text-center text-sm font-medium text-brand-ink transition-colors hover:bg-surface"
        >
          View all notifications
        </Link>
      </div>
    </div>
  );
}
