import type { Metadata } from "next";
import Link from "next/link";
import { Container } from "@/components/layout/container";
import { NotificationsView } from "@/components/notifications/notifications-view";

export const metadata: Metadata = {
  title: "Notifications",
  description: "Your Bimaya updates on policies, payments, and claims.",
  robots: { index: false, follow: false },
};

export default function NotificationsPage() {
  return (
    <Container className="flex-1 py-10 lg:py-14">
      <nav aria-label="Breadcrumb" className="mb-6 text-sm text-muted">
        <Link
          href="/dashboard"
          className="underline-offset-4 transition-colors hover:text-brand-600 hover:underline"
        >
          Dashboard
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-ink">Notifications</span>
      </nav>

      <NotificationsView />
    </Container>
  );
}
