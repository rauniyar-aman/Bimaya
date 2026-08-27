/**
 * Display formatting for money, policy terms and premium frequency.
 *
 * Amounts arrive from the API as decimal strings (e.g. "12000.00"), so every
 * helper accepts a string or a number. Currency uses the South-Asian grouping
 * ("5,00,000") that Nepali customers read fastest.
 */
import type { PremiumFrequency } from "./api";

const nprGroups = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

function toNumber(value: number | string): number {
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(n) ? n : 0;
}

/** "Rs 5,00,000" — whole rupees, South-Asian digit grouping. */
export function formatNpr(value: number | string): string {
  return `Rs ${nprGroups.format(Math.round(toNumber(value)))}`;
}

/** Turn a month count into "1 year", "18 months", "2y 6m". */
export function formatTerm(months: number): string {
  if (!months) return "—";
  if (months < 12) return `${months} month${months === 1 ? "" : "s"}`;
  if (months % 12 === 0) {
    const years = months / 12;
    return `${years} year${years === 1 ? "" : "s"}`;
  }
  return `${Math.floor(months / 12)}y ${months % 12}m`;
}

const FREQUENCY_LABELS: Record<PremiumFrequency, string> = {
  MONTHLY: "per month",
  QUARTERLY: "per quarter",
  YEARLY: "per year",
  ONE_TIME: "one-time",
};

const FREQUENCY_SUFFIX: Record<PremiumFrequency, string> = {
  MONTHLY: "/mo",
  QUARTERLY: "/qtr",
  YEARLY: "/yr",
  ONE_TIME: "",
};

/** "per month", "one-time" — the long form for detail views. */
export function formatFrequency(freq: PremiumFrequency): string {
  return FREQUENCY_LABELS[freq] ?? freq;
}

/** "/mo", "/yr" — the compact suffix shown next to a premium on cards. */
export function frequencySuffix(freq: PremiumFrequency): string {
  return FREQUENCY_SUFFIX[freq] ?? "";
}
