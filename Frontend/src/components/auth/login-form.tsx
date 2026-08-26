"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { AuthFootnote, AuthHeading } from "@/components/auth/auth-heading";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { errorCode, errorMessage, fieldErrors } from "@/lib/api";
import { safeNext } from "@/lib/redirect";

/** Notices set by the screen the user just came from. */
const NOTICES: Record<string, string> = {
  registered: "Your account is verified. Sign in to get started.",
  reset: "Your password has been reset. Sign in with the new one.",
  signedout: "You have been signed out.",
  expired: "Your session expired. Please sign in again.",
};

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { signIn } = useAuth();

  const next = safeNext(params.get("next"));
  const notice = NOTICES[params.get("notice") ?? ""];

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");
    setPending(true);

    try {
      await signIn(email.trim().toLowerCase(), password);
      router.replace(next);
    } catch (error) {
      // An unverified account is a detour, not a failure — send them to finish.
      if (errorCode(error) === "account_unverified") {
        const query = new URLSearchParams({
          email: email.trim().toLowerCase(),
          next,
        });
        router.push(`/verify-otp?${query}`);
        return;
      }

      setErrors(fieldErrors(error));
      setFormError(
        errorMessage(error, "We could not sign you in. Please try again."),
      );
      setPending(false);
    }
  }

  return (
    <>
      <AuthHeading title="Welcome back">
        Sign in to manage your policies, renewals and documents.
      </AuthHeading>

      {notice && (
        <Alert variant="success" className="mb-5">
          {notice}
        </Alert>
      )}

      {formError && (
        <Alert variant="error" className="mb-5">
          {formError}
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <Field label="Email address" htmlFor="email" error={errors.email} required>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? "email-error" : undefined}
            required
          />
        </Field>

        <Field
          label="Password"
          htmlFor="password"
          error={errors.password}
          required
        >
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? "password-error" : undefined}
            required
          />
        </Field>

        <div className="flex justify-end">
          <Link
            href="/forgot-password"
            className="text-sm font-medium text-brand-600 underline-offset-4 hover:underline"
          >
            Forgot password?
          </Link>
        </div>

        <Button type="submit" size="lg" loading={pending} className="w-full">
          {pending ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <AuthFootnote
        prompt="New to Bimaya?"
        href="/register"
        action="Create an account"
      />
    </>
  );
}
