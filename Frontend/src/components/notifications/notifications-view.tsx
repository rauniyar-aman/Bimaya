"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { NotificationRow } from "@/components/notifications/notification-row";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { api, type AppNotification, type Paginated } from "@/lib/api";

const PAGE_SIZE = 12;

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; data: Paginated<AppNotification> };

/** Full-page notification feed with pagination and a mark-all-read action. */
export function NotificationsView() {
  const { authFetch } = useAuth();
  const router = useRouter();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [page, setPage] = useState(1);
  const [marking, setMarking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.notifications
      .list(authFetch, { page })
      .then((data) => {
        if (!cancelled) setState({ phase: "ready", data });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, page]);

  function goToPage(next: number) {
    setState({ phase: "loading" });
    setPage(next);
  }

  async function handleActivate(notification: AppNotification) {
    if (!notification.is_read) {
      setState((prev) => {
        if (prev.phase !== "ready") return prev;
        return {
          phase: "ready",
          data: {
            ...prev.data,
            results: prev.data.results.map((n) =>
              n.id === notification.id ? { ...n, is_read: true } : n,
            ),
          },
        };
      });
      api.notifications.markRead(authFetch, notification.id).catch(() => {});
    }
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
          data: {
            ...prev.data,
            results: prev.data.results.map((n) => ({ ...n, is_read: true })),
          },
        };
      });
    } catch {
      // The next load reconciles the true state.
    } finally {
      setMarking(false);
    }
  }

  const totalPages =
    state.phase === "ready"
      ? Math.max(1, Math.ceil(state.data.count / PAGE_SIZE))
      : 1;
  const hasUnread =
    state.phase === "ready" && state.data.results.some((n) => !n.is_read);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Notifications</h1>
          <p className="mt-1 text-sm text-muted">
            Updates on your policies, payments, and claims.
          </p>
        </div>
        {hasUnread && (
          <Button
            variant="secondary"
            size="sm"
            onClick={handleMarkAll}
            disabled={marking}
          >
            {marking ? "Marking…" : "Mark all read"}
          </Button>
        )}
      </div>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error">
          We could not load your notifications. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.data.results.length === 0 && (
        <Card>
          <CardContent className="py-16 text-center text-sm text-muted">
            You have no notifications yet.
          </CardContent>
        </Card>
      )}

      {state.phase === "ready" && state.data.results.length > 0 && (
        <Card>
          <CardContent className="space-y-1 p-1.5">
            {state.data.results.map((notification) => (
              <NotificationRow
                key={notification.id}
                notification={notification}
                onActivate={handleActivate}
              />
            ))}
          </CardContent>
        </Card>
      )}

      {state.phase === "ready" && totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => goToPage(Math.max(1, page - 1))}
            disabled={page <= 1}
          >
            Previous
          </Button>
          <span className="text-sm text-muted">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => goToPage(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
