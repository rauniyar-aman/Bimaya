"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthFootnote, AuthHeading } from "@/components/auth/auth-heading";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  api,
  errorMessage,
  fieldErrors,
  type RegisterPayload,
  type UserRole,
} from "@/lib/api";
import { cn } from "@/lib/cn";
import { rememberDevCode } from "@/lib/dev-otp";

type SelfServiceRole = Exclude<UserRole, "ADMIN">;

const ROLES: {
  value: SelfServiceRole;
  label: string;
  description: string;
}[] = [
  {
    value: "CUSTOMER",
    label: "I want insurance",
    description: "Compare and buy policies for yourself or your family.",
  },
  {
    value: "PROVIDER",
    label: "I sell insurance",
    description: "List your company's policies and reach new customers.",
  },
];

export function RegisterForm() {
  const router = useRouter();

  const [form, setForm] = useState<RegisterPayload>({
    full_name: "",
    email: "",
    phone: "",
    role: "CUSTOMER",
    password: "",
    confirm_password: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [pending, setPending] = useState(false);

  function update<K extends keyof RegisterPayload>(
    key: K,
    value: RegisterPayload[K],
  ) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");

    if (form.password !== form.confirm_password) {
      setErrors({ confirm_password: "The two passwords do not match." });
      return;
    }

    setPending(true);
    const email = form.email.trim().toLowerCase();

    try {
      const result = await api.auth.register({
        ...form,
        email,
        full_name: form.full_name.trim(),
        phone: form.phone.trim(),
      });
      rememberDevCode(result.dev_otp);
      router.push(`/verify-otp?email=${encodeURIComponent(result.email)}`);
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(
        errorMessage(error, "We could not create your account. Please try again."),
      );
      setPending(false);
    }
  }

  return (
    <>
      <AuthHeading title="Create your Bimaya account">
        It takes a minute. You will get a verification code by email.
      </AuthHeading>

      {formError && (
        <Alert variant="error" className="mb-5">
          {formError}
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-ink">
            How will you use Bimaya?
          </legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {ROLES.map((role) => {
              const selected = form.role === role.value;
              return (
                <label
                  key={role.value}
                  className={cn(
                    "cursor-pointer rounded-xl border p-3.5 transition-colors focus-within:ring-2 focus-within:ring-brand-100",
                    selected
                      ? "border-brand-400 bg-brand-50"
                      : "border-line bg-white hover:border-brand-200",
                  )}
                >
                  <input
                    type="radio"
                    name="role"
                    value={role.value}
                    checked={selected}
                    onChange={() => update("role", role.value)}
                    className="sr-only"
                  />
                  <span
                    className={cn(
                      "block text-sm font-medium",
                      selected ? "text-brand-700" : "text-ink",
                    )}
                  >
                    {role.label}
                  </span>
                  <span className="mt-1 block text-xs leading-relaxed text-muted">
                    {role.description}
                  </span>
                </label>
              );
            })}
          </div>
          {errors.role && (
            <p role="alert" className="text-sm text-red-600">
              {errors.role}
            </p>
          )}
        </fieldset>

        <Field
          label="Full name"
          htmlFor="full_name"
          error={errors.full_name}
          required
        >
          <Input
            id="full_name"
            name="full_name"
            autoComplete="name"
            placeholder="Sita Sharma"
            value={form.full_name}
            onChange={(e) => update("full_name", e.target.value)}
            aria-invalid={Boolean(errors.full_name)}
            required
          />
        </Field>

        <Field label="Email address" htmlFor="email" error={errors.email} required>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={form.email}
            onChange={(e) => update("email", e.target.value)}
            aria-invalid={Boolean(errors.email)}
            required
          />
        </Field>

        <Field
          label="Mobile number"
          htmlFor="phone"
          error={errors.phone}
          hint="Optional — we use it for policy reminders."
        >
          <Input
            id="phone"
            name="phone"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            placeholder="98XXXXXXXX"
            value={form.phone}
            onChange={(e) => update("phone", e.target.value)}
            aria-invalid={Boolean(errors.phone)}
          />
        </Field>

        <Field
          label="Password"
          htmlFor="password"
          error={errors.password}
          hint="At least 8 characters, and not something easy to guess."
          required
        >
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            value={form.password}
            onChange={(e) => update("password", e.target.value)}
            aria-invalid={Boolean(errors.password)}
            required
          />
        </Field>

        <Field
          label="Confirm password"
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
            value={form.confirm_password}
            onChange={(e) => update("confirm_password", e.target.value)}
            aria-invalid={Boolean(errors.confirm_password)}
            required
          />
        </Field>

        <Button
          type="submit"
          variant="cta"
          size="lg"
          loading={pending}
          className="w-full"
        >
          {pending ? "Creating account…" : "Create account"}
        </Button>

        <p className="text-xs leading-relaxed text-muted">
          By creating an account you agree to Bimaya&apos;s Terms of Service and
          Privacy Policy.
        </p>
      </form>

      <AuthFootnote
        prompt="Already have an account?"
        href="/login"
        action="Sign in"
      />
    </>
  );
}
