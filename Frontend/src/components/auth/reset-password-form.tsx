"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { AuthFootnote, AuthHeading } from "@/components/auth/auth-heading";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { api, errorMessage, fieldErrors } from "@/lib/api";
import { useDevCode } from "@/lib/dev-otp";

export function ResetPasswordForm() {
  const router = useRouter();
  const params = useSearchParams();
  const devCode = useDevCode();

  const [email, setEmail] = useState(params.get("email") ?? "");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");

    if (password !== confirmPassword) {
      setErrors({ confirm_password: "The two passwords do not match." });
      return;
    }

    setPending(true);

    try {
      await api.auth.confirmPasswordReset({
        email: email.trim().toLowerCase(),
        code: code.trim(),
        new_password: password,
        confirm_password: confirmPassword,
      });
      router.replace("/login?notice=reset");
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(
        errorMessage(error, "We could not reset your password. Please try again."),
      );
      setPending(false);
    }
  }

  return (
    <>
      <AuthHeading title="Choose a new password">
        Enter the code we emailed you, then pick a password you have not used
        before.
      </AuthHeading>

      {devCode && (
        <Alert variant="info" className="mb-5">
          Development mode — your reset code is{" "}
          <strong className="font-semibold tracking-widest">{devCode}</strong>
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
          label="Reset code"
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
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            className="text-center text-lg font-semibold tracking-[0.5em]"
            aria-invalid={Boolean(errors.code)}
            autoFocus
            required
          />
        </Field>

        <Field
          label="New password"
          htmlFor="new_password"
          error={errors.new_password}
          hint="At least 8 characters, and not something easy to guess."
          required
        >
          <Input
            id="new_password"
            name="new_password"
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={Boolean(errors.new_password)}
            required
          />
        </Field>

        <Field
          label="Confirm new password"
          htmlFor="confirm_password"
          error={errors.confirm_password}
          required
        >
          <Input
            id="confirm_password"
            name="confirm_password"
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            aria-invalid={Boolean(errors.confirm_password)}
            required
          />
        </Field>

        <Button type="submit" size="lg" loading={pending} className="w-full">
          {pending ? "Saving…" : "Reset password"}
        </Button>

        <p className="text-xs leading-relaxed text-muted">
          Resetting your password signs you out everywhere else.
        </p>
      </form>

      <AuthFootnote
        prompt="Need a new code?"
        href="/forgot-password"
        action="Request another"
      />
    </>
  );
}
