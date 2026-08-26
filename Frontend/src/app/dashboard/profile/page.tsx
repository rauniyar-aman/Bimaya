import type { Metadata } from "next";
import Link from "next/link";
import { ChangePasswordForm } from "@/components/dashboard/change-password-form";
import { ProfileForm } from "@/components/dashboard/profile-form";
import { Container } from "@/components/layout/container";

export const metadata: Metadata = {
  title: "Profile settings",
  description: "Update your Bimaya contact details and password.",
  robots: { index: false, follow: false },
};

export default function ProfileSettingsPage() {
  return (
    <Container className="flex-1 py-10 lg:py-14">
      <nav aria-label="Breadcrumb" className="text-sm text-muted">
        <Link
          href="/dashboard"
          className="underline-offset-4 transition-colors hover:text-brand-600 hover:underline"
        >
          Dashboard
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-ink">Profile settings</span>
      </nav>

      <h1 className="mt-3 font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
        Profile settings
      </h1>
      <p className="mt-1.5 text-sm text-muted">
        Keep your contact details current so we can reach you about renewals and
        claims.
      </p>

      <div className="mt-8 grid max-w-4xl gap-6 lg:grid-cols-2">
        <ProfileForm />
        <ChangePasswordForm />
      </div>
    </Container>
  );
}
