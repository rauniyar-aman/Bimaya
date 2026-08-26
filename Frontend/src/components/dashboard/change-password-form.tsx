"use client";

import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { type MessageResponse, errorMessage, fieldErrors } from "@/lib/api";

const EMPTY = {
  current_password: "",
  new_password: "",
  confirm_password: "",
};

export function ChangePasswordForm() {
  const { authFetch } = useAuth();

  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState(false);

  function update(key: keyof typeof EMPTY, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");
    setNotice("");

    if (form.new_password !== form.confirm_password) {
      setErrors({ confirm_password: "The two passwords do not match." });
      return;
    }

    setPending(true);

    try {
      const result = await authFetch<MessageResponse>("/auth/change-password/", {
        method: "POST",
        json: form,
      });
      setNotice(result.detail);
      setForm(EMPTY);
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(
        errorMessage(error, "We could not change your password. Please try again."),
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Password</CardTitle>
        <p className="mt-1.5 text-sm text-muted">
          Pick something long that you do not use anywhere else.
        </p>
      </CardHeader>

      <CardContent>
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
          <Field
            label="Current password"
            htmlFor="current_password"
            error={errors.current_password}
            required
          >
            <Input
              id="current_password"
              name="current_password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              value={form.current_password}
              onChange={(e) => update("current_password", e.target.value)}
              aria-invalid={Boolean(errors.current_password)}
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
              value={form.new_password}
              onChange={(e) => update("new_password", e.target.value)}
              aria-invalid={Boolean(errors.new_password)}
              required
            />
          </Field>

          <Field
            label="Confirm new password"
            htmlFor="confirm_new_password"
            error={errors.confirm_password}
            required
          >
            <Input
              id="confirm_new_password"
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

          <Button type="submit" loading={pending}>
            {pending ? "Updating…" : "Update password"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
