"use client";

import { useState } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  errorMessage,
  fieldErrors,
  type ContactLeadInput,
} from "@/lib/api";

const EMPTY: ContactLeadInput = {
  contact_name: "",
  email: "",
  phone: "",
  message: "",
};

export function ContactForm() {
  const [form, setForm] = useState<ContactLeadInput>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);

  function update<K extends keyof ContactLeadInput>(
    key: K,
    value: ContactLeadInput[K],
  ) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");
    setPending(true);

    try {
      await api.leads.contact({
        contact_name: form.contact_name.trim(),
        email: form.email.trim().toLowerCase(),
        phone: form.phone?.trim() || undefined,
        message: form.message?.trim() || undefined,
      });
      setDone(true);
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(
        errorMessage(error, "We could not send your message. Please try again."),
      );
      setPending(false);
    }
  }

  if (done) {
    return (
      <Alert variant="success">
        Thanks for reaching out — we have received your message and will get
        back to you soon.
      </Alert>
    );
  }

  return (
    <>
      {formError && (
        <Alert variant="error" className="mb-5">
          {formError}
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <Field
          label="Your name"
          htmlFor="contact_name"
          error={errors.contact_name}
          required
        >
          <Input
            id="contact_name"
            name="contact_name"
            autoComplete="name"
            placeholder="Sita Sharma"
            value={form.contact_name}
            onChange={(e) => update("contact_name", e.target.value)}
            aria-invalid={Boolean(errors.contact_name)}
            required
          />
        </Field>

        <Field label="Email" htmlFor="email" error={errors.email} required>
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
          label="Phone"
          htmlFor="phone"
          error={errors.phone}
          hint="Optional — a number we can reach you on."
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
          label="Message"
          htmlFor="message"
          error={errors.message}
          required
        >
          <Textarea
            id="message"
            name="message"
            rows={5}
            placeholder="How can we help?"
            value={form.message}
            onChange={(e) => update("message", e.target.value)}
            aria-invalid={Boolean(errors.message)}
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
          {pending ? "Sending message…" : "Send message"}
        </Button>
      </form>
    </>
  );
}
