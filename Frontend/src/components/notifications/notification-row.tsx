import { metaFor, NOTIFICATION_TONE_CLASSES } from "@/components/notifications/notification-meta";
import { cn } from "@/lib/cn";
import { formatRelativeTime } from "@/lib/date";
import type { AppNotification } from "@/lib/api";

interface NotificationRowProps {
  notification: AppNotification;
  onActivate: (notification: AppNotification) => void;
  /** Tighter padding for the header dropdown; roomier for the full feed. */
  compact?: boolean;
}

/** A single notification line: icon chip, title, body, relative time. */
export function NotificationRow({
  notification,
  onActivate,
  compact = false,
}: NotificationRowProps) {
  const meta = metaFor(notification.type);
  const Icon = meta.icon;
  const interactive = Boolean(notification.url);

  const content = (
    <>
      <span
        className={cn(
          "flex shrink-0 items-center justify-center rounded-full",
          compact ? "h-8 w-8" : "h-10 w-10",
          NOTIFICATION_TONE_CLASSES[meta.tone],
        )}
      >
        <Icon width={compact ? 16 : 18} height={compact ? 16 : 18} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline gap-2">
          <span
            className={cn(
              "truncate text-sm font-medium text-ink",
              !notification.is_read && "font-semibold",
            )}
          >
            {notification.title}
          </span>
          {!notification.is_read && (
            <span
              aria-hidden="true"
              className="ml-auto h-2 w-2 shrink-0 rounded-full bg-brand-500"
            />
          )}
        </span>
        {notification.body && (
          <span
            className={cn(
              "mt-0.5 block text-sm text-muted",
              compact && "line-clamp-2",
            )}
          >
            {notification.body}
          </span>
        )}
        <span className="mt-1 block text-xs text-muted">
          {formatRelativeTime(notification.created_at)}
        </span>
      </span>
    </>
  );

  const base = cn(
    "flex w-full gap-3 rounded-xl px-3 py-2.5 text-left transition-colors",
    !notification.is_read && "bg-brand-50/40",
  );

  if (!interactive) {
    return <div className={base}>{content}</div>;
  }

  return (
    <button
      type="button"
      onClick={() => onActivate(notification)}
      className={cn(base, "hover:bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400")}
    >
      {content}
    </button>
  );
}
