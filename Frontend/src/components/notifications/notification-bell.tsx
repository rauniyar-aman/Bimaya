"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { BellIcon } from "@/components/icons";
import { NotificationPanel } from "@/components/notifications/notification-panel";
import { cn } from "@/lib/cn";
import { api } from "@/lib/api";

/** How often we re-poll the unread count while the tab is open. */
const POLL_MS = 60_000;

/** Header bell button with an unread-count badge and a dropdown panel. */
export function NotificationBell() {
  const { authFetch, isAuthenticated } = useAuth();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const refreshCount = useCallback(() => {
    if (!isAuthenticated) return;
    api.notifications
      .unreadCount(authFetch)
      .then(({ count }) => setUnread(count))
      .catch(() => {
        // A transient count fetch failure is not worth surfacing in the header.
      });
  }, [authFetch, isAuthenticated]);

  // Poll the unread count on mount, on an interval, and whenever the tab is
  // brought back to the foreground.
  useEffect(() => {
    if (!isAuthenticated) return;
    refreshCount();
    const timer = window.setInterval(refreshCount, POLL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") refreshCount();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [isAuthenticated, refreshCount]);

  // Close on outside click or Escape, the way a native menu behaves.
  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent | TouchEvent) {
      if (!wrapperRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (!isAuthenticated) return null;

  const badge = unread > 99 ? "99+" : String(unread);

  return (
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={
          unread > 0 ? `Notifications, ${unread} unread` : "Notifications"
        }
        className={cn(
          "relative flex h-10 w-10 items-center justify-center rounded-full border border-line text-ink transition-colors hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2",
          open && "bg-surface",
        )}
      >
        <BellIcon width={20} height={20} />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex min-w-[18px] items-center justify-center rounded-full bg-brand-500 px-1 text-[10px] font-semibold leading-4 text-white">
            {badge}
          </span>
        )}
      </button>

      {open && (
        <NotificationPanel
          onClose={() => setOpen(false)}
          onCountChange={setUnread}
        />
      )}
    </div>
  );
}
