import type { ReactNode } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { StatCard, type StatTone } from "@/components/ui/stat-card";
import { BarChart, ColumnChart } from "@/components/analytics/bar-chart";
import {
  BadgeCheckIcon,
  BuildingIcon,
  ChartIcon,
  ClipboardIcon,
  FileTextIcon,
  ShieldCheckIcon,
  UsersIcon,
  WalletIcon,
} from "@/components/icons";
import type { AnalyticsBreakdown, AnalyticsData, AnalyticsStat } from "@/lib/api";
import { formatNpr } from "@/lib/format";

/** Icon + colour for each known stat key, across the admin and provider payloads. */
const STAT_META: Record<string, { icon: ReactNode; tone: StatTone }> = {
  users: { icon: <UsersIcon className="h-5 w-5" />, tone: "brand" },
  providers: { icon: <BuildingIcon className="h-5 w-5" />, tone: "brand" },
  policies: { icon: <FileTextIcon className="h-5 w-5" />, tone: "brand" },
  purchases: { icon: <ClipboardIcon className="h-5 w-5" />, tone: "brand" },
  active: { icon: <BadgeCheckIcon className="h-5 w-5" />, tone: "success" },
  claims: { icon: <ShieldCheckIcon className="h-5 w-5" />, tone: "brand" },
  premium: { icon: <WalletIcon className="h-5 w-5" />, tone: "success" },
  commission: { icon: <WalletIcon className="h-5 w-5" />, tone: "brand" },
  settled: { icon: <WalletIcon className="h-5 w-5" />, tone: "accent" },
};

const FALLBACK_META = { icon: <ChartIcon className="h-5 w-5" />, tone: "muted" as StatTone };

function statValue(stat: AnalyticsStat): ReactNode {
  return stat.format === "currency" ? formatNpr(stat.value) : stat.value;
}

/**
 * Renders an analytics payload as stat cards, a monthly trend and status
 * breakdowns. Props-driven so the admin and provider dashboards share it; the
 * platform-only "users by role" breakdown renders only when present.
 */
export function AnalyticsPanel({
  data,
}: {
  data: AnalyticsData & { users_by_role?: AnalyticsBreakdown[] };
}) {
  const months = data.monthly.map((m) => ({
    label: m.label,
    value: m.purchases,
    valueLabel: String(m.purchases),
    caption: formatNpr(m.premium),
  }));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data.stats.map((stat) => {
          const meta = STAT_META[stat.key] ?? FALLBACK_META;
          return (
            <StatCard
              key={stat.key}
              label={stat.label}
              value={statValue(stat)}
              tone={meta.tone}
              icon={meta.icon}
            />
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Purchases over time</CardTitle>
        </CardHeader>
        <CardContent>
          <ColumnChart
            data={months}
            ariaLabel="Monthly purchases over the last six months, with premium collected"
          />
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Purchases by status</CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart
              data={data.purchases_by_status}
              ariaLabel="Purchases by status"
              tone="brand"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Claims by status</CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart
              data={data.claims_by_status}
              ariaLabel="Claims by status"
              tone="accent"
              emptyLabel="No claims filed yet."
            />
          </CardContent>
        </Card>

        {data.users_by_role && (
          <Card>
            <CardHeader>
              <CardTitle>Users by role</CardTitle>
            </CardHeader>
            <CardContent>
              <BarChart
                data={data.users_by_role}
                ariaLabel="Users by role"
                tone="success"
              />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
