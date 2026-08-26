import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthFormFallback } from "@/components/auth/auth-form-fallback";
import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = {
  title: "Sign in",
  description:
    "Sign in to Bimaya to manage your insurance policies, renewals and documents.",
  robots: { index: false, follow: true },
};

export default function LoginPage() {
  return (
    <Suspense fallback={<AuthFormFallback fields={2} />}>
      <LoginForm />
    </Suspense>
  );
}
