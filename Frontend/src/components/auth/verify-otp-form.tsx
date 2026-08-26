"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthFootnote, AuthHeading } from "@/components/auth/auth-heading";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { api, errorMessage, fieldErrors } from "@/lib/api";
import { rememberDevCode, useDevCode } from "@/lib/dev-otp";
import { safeNext } from "@/lib/redirect";

const RESEND_COOLDOWN_SECONDS = 45;

export function VerifyOtpForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { completeVerification } = useAuth();

  const next = safeNext(params.get("next"));
  const devCode = useDevCode();
  const [email, setEmail] = useState(params.get("email") ?? "");
  const [code, setCode] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");
    setNotice("");
    setPending(true);

    try {
      await completeVerification(email.trim().toLowerCase(), code.trim());
      router.replace(next);
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(
        errorMessage(error, "We could not verify that code. Please try again."),
      );
      setPending(false);
    }
  }

  async function handleResend() {
    setErrors({});
    setFormError("");
    setNotice("");
    setResending(true);

    try {
      const result = await api.auth.resendOtp(email.trim().toLowerCase());
      setNotice(result.detail);
      setCooldown(RESEND_COOLDOWN_SECONDS);
      rememberDevCode(result.dev_otp);
    } catch (error) {
      setFormError(
        errorMessage(error, "We could not send a new code just yet."),
      );
    } finally {
      setResending(false);
    }
  }

  return (
    <>
      <AuthHeading title="Verify your account">
        {email ? (
          <>
            We sent a 6-digit code to <strong className="text-ink">{email}</strong>.
            Enter it below to finish signing up.
          </>
        ) : (
          "Enter your email and the 6-digit code we sent you."
        )}
      </AuthHeading>

      {devCode && (
        <Alert variant="info" className="mb-5">
          Development mode — your code is{" "}
          <strong className="font-semibold tracking-widest">{devCode}</strong>
        </Alert>
      )}

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
            required
          />
        </Field>

        <Field
          label="Verification code"
          htmlFor="code"
          error={errors.code}
          hint="The code expires in 10 minutes."
          required
        >
          <Input
            id="code"
            name="code"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            placeholder="000000"
            value={code}
            // Strip anything that is not a digit so pasted codes still work.
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            className="text-center text-lg font-semibold tracking-[0.5em]"
            aria-invalid={Boolean(errors.code)}
            autoFocus
            required
          />
        </Field>

        <Button
          type="submit"
          size="lg"
          loading={pending}
          disabled={code.length < 4}
          className="w-full"
        >
          {pending ? "Verifying…" : "Verify and continue"}
        </Button>
      </form>

      <div className="mt-6 text-center text-sm text-muted">
        Did not get the code?{" "}
        <button
          type="button"
          onClick={handleResend}
          disabled={resending || cooldown > 0 || !email}
          className="font-medium text-brand-600 underline-offset-4 hover:underline disabled:cursor-not-allowed disabled:text-muted disabled:no-underline"
        >
          {cooldown > 0 ? `Resend in ${cooldown}s` : "Send a new one"}
        </button>
      </div>

      <AuthFootnote
        prompt="Wrong email?"
        href="/register"
        action="Start over"
      />
    </>
  );
}
