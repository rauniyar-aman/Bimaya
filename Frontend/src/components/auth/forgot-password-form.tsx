"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthFootnote, AuthHeading } from "@/components/auth/auth-heading";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { api, errorMessage, fieldErrors } from "@/lib/api";
import { rememberDevCode } from "@/lib/dev-otp";

export function ForgotPasswordForm() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");
    setPending(true);

    const address = email.trim().toLowerCase();

    try {
      const result = await api.auth.requestPasswordReset(address);
      rememberDevCode(result.dev_otp);
      // The API deliberately answers the same way whether or not the account
      // exists, so the next screen is always shown.
      router.push(`/reset-password?email=${encodeURIComponent(address)}`);
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(
        errorMessage(error, "We could not send a reset code. Please try again."),
      );
      setPending(false);
    }
  }

  return (
    <>
      <AuthHeading title="Reset your password">
        Enter the email you signed up with and we will send you a reset code.
      </AuthHeading>

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
            autoFocus
            required
          />
        </Field>

        <Button type="submit" size="lg" loading={pending} className="w-full">
          {pending ? "Sending code…" : "Send reset code"}
        </Button>
      </form>

      <AuthFootnote
        prompt="Remembered it?"
        href="/login"
        action="Back to sign in"
      />
    </>
  );
}
