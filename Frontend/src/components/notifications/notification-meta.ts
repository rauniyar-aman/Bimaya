import type { ComponentType, SVGProps } from "react";
import {
  BadgeCheckIcon,
  BellIcon,
  ClipboardIcon,
  FileTextIcon,
  ShieldCheckIcon,
  WalletIcon,
  XIcon,
} from "@/components/icons";
import type { NotificationType } from "@/lib/api";

type IconComponent = ComponentType<SVGProps<SVGSVGElement>>;

/** Colour emphasis for a notification's icon chip. */
export type NotificationTone = "brand" | "success" | "danger" | "accent" | "muted";

interface NotificationMeta {
  icon: IconComponent;
  tone: NotificationTone;
}

/** Per-type icon + tone for the bell panel and the full feed. */
export const NOTIFICATION_TYPE_META: Record<NotificationType, NotificationMeta> = {
  WELCOME: { icon: BellIcon, tone: "brand" },
  PURCHASE_CREATED: { icon: ClipboardIcon, tone: "brand" },
  PAYMENT_CONFIRMED: { icon: WalletIcon, tone: "success" },
  PAYMENT_FAILED: { icon: WalletIcon, tone: "danger" },
  PURCHASE_FORWARDED: { icon: ClipboardIcon, tone: "accent" },
  POLICY_ISSUED: { icon: ShieldCheckIcon, tone: "success" },
  RENEWAL_REMINDER: { icon: BellIcon, tone: "accent" },
  CLAIM_SUBMITTED: { icon: FileTextIcon, tone: "brand" },
  CLAIM_UNDER_REVIEW: { icon: FileTextIcon, tone: "accent" },
  CLAIM_MORE_INFO: { icon: FileTextIcon, tone: "accent" },
  CLAIM_APPROVED: { icon: BadgeCheckIcon, tone: "success" },
  CLAIM_REJECTED: { icon: XIcon, tone: "danger" },
  CLAIM_SETTLED: { icon: WalletIcon, tone: "success" },
  KYC_VERIFIED: { icon: BadgeCheckIcon, tone: "success" },
  KYC_REJECTED: { icon: XIcon, tone: "danger" },
  PROVIDER_APPROVED: { icon: BadgeCheckIcon, tone: "success" },
  PROVIDER_NEW_ISSUANCE: { icon: ClipboardIcon, tone: "brand" },
  PROVIDER_NEW_CLAIM: { icon: FileTextIcon, tone: "brand" },
};

/** Fallback for any unmapped / unknown type coming from the API. */
export const DEFAULT_NOTIFICATION_META: NotificationMeta = {
  icon: BellIcon,
  tone: "muted",
};

/** Tailwind classes for the round icon chip, keyed by tone. */
export const NOTIFICATION_TONE_CLASSES: Record<NotificationTone, string> = {
  brand: "bg-brand-50 text-brand-600",
  success: "bg-success-50 text-success-700",
  danger: "bg-danger-surface text-danger",
  accent: "bg-accent-50 text-accent-700",
  muted: "bg-surface text-muted",
};

export function metaFor(type: NotificationType): NotificationMeta {
  return NOTIFICATION_TYPE_META[type] ?? DEFAULT_NOTIFICATION_META;
}
