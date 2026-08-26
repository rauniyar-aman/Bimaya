import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthFormFallback } from "@/components/auth/auth-form-fallback";
import { VerifyOtpForm } from "@/components/auth/verify-otp-form";

export const metadata: Metadata = {
  title: "Verify your account",
  description: "Enter the verification code we sent to finish setting up your Bimaya account.",
  robots: { index: false, follow: false },
};

export default function VerifyOtpPage() {
  return (
    <Suspense fallback={<AuthFormFallback fields={2} />}>
      <VerifyOtpForm />
    </Suspense>
  );
}
