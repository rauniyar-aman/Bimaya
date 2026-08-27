"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  errorMessage,
  fieldErrors,
  type InsuranceCategory,
  type PremiumFrequency,
  type ProviderPolicy,
  type ProviderPolicyInput,
} from "@/lib/api";

const FREQUENCIES: { value: PremiumFrequency; label: string }[] = [
  { value: "MONTHLY", label: "Monthly" },
  { value: "QUARTERLY", label: "Quarterly" },
  { value: "YEARLY", label: "Yearly" },
  { value: "ONE_TIME", label: "One-time" },
];

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export function PolicyForm({
  categories,
  policy,
}: {
  categories: InsuranceCategory[];
  policy?: ProviderPolicy;
}) {
  const { authFetch } = useAuth();
  const router = useRouter();
  const isEdit = Boolean(policy);

  const [name, setName] = useState(policy?.name ?? "");
  const [categoryId, setCategoryId] = useState(
    policy ? String(policy.category) : "",
  );
  const [summary, setSummary] = useState(policy?.summary ?? "");
  const [description, setDescription] = useState(policy?.description ?? "");
  const [premium, setPremium] = useState(policy?.premium ?? "");
  const [frequency, setFrequency] = useState<PremiumFrequency>(
    policy?.premium_frequency ?? "YEARLY",
  );
  const [coverage, setCoverage] = useState(policy?.coverage_amount ?? "");
  const [termMonths, setTermMonths] = useState(
    policy ? String(policy.term_months) : "",
  );
  const [minAge, setMinAge] = useState(
    policy?.min_age != null ? String(policy.min_age) : "",
  );
  const [maxAge, setMaxAge] = useState(
    policy?.max_age != null ? String(policy.max_age) : "",
  );
  const [features, setFeatures] = useState((policy?.features ?? []).join("\n"));
  const [addOns, setAddOns] = useState((policy?.add_ons ?? []).join("\n"));
  const [terms, setTerms] = useState(policy?.terms ?? "");

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    setFormError("");
    setPending(true);

    const payload: ProviderPolicyInput = {
      name: name.trim(),
      summary: summary.trim(),
      description: description.trim(),
      category: Number(categoryId),
      premium: premium.trim(),
      premium_frequency: frequency,
      coverage_amount: coverage.trim(),
      term_months: Number(termMonths) || 0,
      min_age: minAge.trim() ? Number(minAge) : null,
      max_age: maxAge.trim() ? Number(maxAge) : null,
      features: splitLines(features),
      add_ons: splitLines(addOns),
      terms: terms.trim(),
    };

    try {
      if (policy) {
        await api.provider.updatePolicy(authFetch, policy.id, payload);
      } else {
        await api.provider.createPolicy(authFetch, payload);
      }
      router.push("/provider");
    } catch (error) {
      setErrors(fieldErrors(error));
      setFormError(
        errorMessage(error, "We could not save this policy. Please try again."),
      );
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isEdit ? "Edit policy" : "New policy"}</CardTitle>
        <p className="mt-1.5 text-sm text-muted">
          {isEdit
            ? "Editing a live plan sends it back for a quick review before it is public again."
            : "Save as a draft, then submit it for review when you are ready to go live."}
        </p>
      </CardHeader>

      <CardContent>
        {formError && (
          <Alert variant="error" className="mb-5">
            {formError}
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <Field label="Plan name" htmlFor="name" error={errors.name} required>
            <Input
              id="name"
              name="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Everest Term Life 20"
              aria-invalid={Boolean(errors.name)}
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Category"
              htmlFor="category"
              error={errors.category}
              required
            >
              <Select
                id="category"
                name="category"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                aria-invalid={Boolean(errors.category)}
              >
                <option value="" disabled>
                  Choose a category
                </option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </Select>
            </Field>

            <Field
              label="Tagline"
              htmlFor="summary"
              error={errors.summary}
              hint="One line shown on the plan card."
            >
              <Input
                id="summary"
                name="summary"
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="Affordable cover for your family's future."
                aria-invalid={Boolean(errors.summary)}
              />
            </Field>
          </div>

          <Field
            label="Description"
            htmlFor="policy_description"
            error={errors.description}
          >
            <Textarea
              id="policy_description"
              name="description"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Explain what this plan covers and who it is for."
              aria-invalid={Boolean(errors.description)}
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Premium (Rs)"
              htmlFor="premium"
              error={errors.premium}
              required
            >
              <Input
                id="premium"
                name="premium"
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                value={premium}
                onChange={(e) => setPremium(e.target.value)}
                placeholder="12000"
                aria-invalid={Boolean(errors.premium)}
              />
            </Field>

            <Field
              label="Premium frequency"
              htmlFor="premium_frequency"
              error={errors.premium_frequency}
              required
            >
              <Select
                id="premium_frequency"
                name="premium_frequency"
                value={frequency}
                onChange={(e) =>
                  setFrequency(e.target.value as PremiumFrequency)
                }
              >
                {FREQUENCIES.map((f) => (
                  <option key={f.value} value={f.value}>
                    {f.label}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Coverage amount (Rs)"
              htmlFor="coverage_amount"
              error={errors.coverage_amount}
              required
            >
              <Input
                id="coverage_amount"
                name="coverage_amount"
                type="number"
                inputMode="decimal"
                min="0"
                step="0.01"
                value={coverage}
                onChange={(e) => setCoverage(e.target.value)}
                placeholder="2500000"
                aria-invalid={Boolean(errors.coverage_amount)}
              />
            </Field>

            <Field
              label="Term (months)"
              htmlFor="term_months"
              error={errors.term_months}
              required
            >
              <Input
                id="term_months"
                name="term_months"
                type="number"
                inputMode="numeric"
                min="1"
                step="1"
                value={termMonths}
                onChange={(e) => setTermMonths(e.target.value)}
                placeholder="240"
                aria-invalid={Boolean(errors.term_months)}
              />
            </Field>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Minimum age"
              htmlFor="min_age"
              error={errors.min_age}
              hint="Leave blank if there is no minimum."
            >
              <Input
                id="min_age"
                name="min_age"
                type="number"
                inputMode="numeric"
                min="0"
                max="120"
                step="1"
                value={minAge}
                onChange={(e) => setMinAge(e.target.value)}
                placeholder="18"
                aria-invalid={Boolean(errors.min_age)}
              />
            </Field>

            <Field
              label="Maximum age"
              htmlFor="max_age"
              error={errors.max_age}
              hint="Leave blank if there is no maximum."
            >
              <Input
                id="max_age"
                name="max_age"
                type="number"
                inputMode="numeric"
                min="0"
                max="120"
                step="1"
                value={maxAge}
                onChange={(e) => setMaxAge(e.target.value)}
                placeholder="60"
                aria-invalid={Boolean(errors.max_age)}
              />
            </Field>
          </div>

          <Field
            label="What's covered"
            htmlFor="features"
            error={errors.features}
            hint="One benefit per line."
          >
            <Textarea
              id="features"
              name="features"
              rows={4}
              value={features}
              onChange={(e) => setFeatures(e.target.value)}
              placeholder={"Death benefit up to sum assured\nTax benefits\n24x7 support"}
              aria-invalid={Boolean(errors.features)}
            />
          </Field>

          <Field
            label="Optional add-ons"
            htmlFor="add_ons"
            error={errors.add_ons}
            hint="One add-on per line. Leave blank if none."
          >
            <Textarea
              id="add_ons"
              name="add_ons"
              rows={3}
              value={addOns}
              onChange={(e) => setAddOns(e.target.value)}
              placeholder={"Accidental death rider\nCritical illness cover"}
              aria-invalid={Boolean(errors.add_ons)}
            />
          </Field>

          <Field
            label="Terms & conditions"
            htmlFor="terms"
            error={errors.terms}
          >
            <Textarea
              id="terms"
              name="terms"
              rows={4}
              value={terms}
              onChange={(e) => setTerms(e.target.value)}
              placeholder="Key exclusions, waiting periods and conditions."
              aria-invalid={Boolean(errors.terms)}
            />
          </Field>

          <div className="flex items-center gap-3 pt-2">
            <Button type="submit" loading={pending}>
              {isEdit ? "Save changes" : "Save as draft"}
            </Button>
            <Link
              href="/provider"
              className={buttonVariants({ variant: "secondary", size: "md" })}
            >
              Cancel
            </Link>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
