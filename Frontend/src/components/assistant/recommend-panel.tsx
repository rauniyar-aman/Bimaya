"use client";

import { useEffect, useState } from "react";
import { PolicyCard } from "@/components/marketplace/policy-card";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import {
  api,
  errorMessage,
  type InsuranceCategory,
  type RecommendationInput,
  type RecommendedPolicy,
} from "@/lib/api";

type State =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "error"; message: string }
  | { phase: "ready"; picks: RecommendedPolicy[] };

/**
 * The rule-based advisor form. The visitor describes what they need (category,
 * budget, age, minimum cover) and we rank the live catalog for them — no LLM,
 * so the numbers always come straight from the listed policies.
 */
export function RecommendPanel() {
  const [categories, setCategories] = useState<InsuranceCategory[]>([]);
  const [category, setCategory] = useState("");
  const [budget, setBudget] = useState("");
  const [age, setAge] = useState("");
  const [coverage, setCoverage] = useState("");
  const [state, setState] = useState<State>({ phase: "idle" });

  // Populate the category dropdown from the public catalog.
  useEffect(() => {
    let cancelled = false;
    api.categories
      .list()
      .then((rows) => {
        if (!cancelled) setCategories(rows);
      })
      .catch(() => {
        // A missing dropdown is not fatal — the visitor can still search
        // across every category.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setState({ phase: "loading" });

    const payload: RecommendationInput = {};
    if (category) payload.category = category;
    if (budget.trim()) payload.budget_max = budget.trim();
    if (age.trim()) payload.age = age.trim();
    if (coverage.trim()) payload.coverage_min = coverage.trim();

    try {
      const picks = await api.assistant.recommend(payload);
      setState({ phase: "ready", picks });
    } catch (error) {
      setState({
        phase: "error",
        message: errorMessage(
          error,
          "We could not fetch recommendations just now. Please try again.",
        ),
      });
    }
  }

  return (
    <div className="space-y-8">
      <form
        onSubmit={handleSubmit}
        className="grid gap-4 rounded-2xl border border-line bg-white p-5 shadow-sm sm:grid-cols-2 lg:grid-cols-4"
      >
        <Field label="Type of cover" htmlFor="advisor-category">
          <Select
            id="advisor-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">Any category</option>
            {categories.map((c) => (
              <option key={c.id} value={c.slug}>
                {c.name}
              </option>
            ))}
          </Select>
        </Field>

        <Field
          label="Budget per premium"
          htmlFor="advisor-budget"
          hint="Max you want to pay (NPR)"
        >
          <Input
            id="advisor-budget"
            type="number"
            inputMode="numeric"
            min={0}
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            placeholder="e.g. 15000"
          />
        </Field>

        <Field label="Your age" htmlFor="advisor-age">
          <Input
            id="advisor-age"
            type="number"
            inputMode="numeric"
            min={0}
            max={120}
            value={age}
            onChange={(e) => setAge(e.target.value)}
            placeholder="e.g. 32"
          />
        </Field>

        <Field
          label="Minimum cover"
          htmlFor="advisor-coverage"
          hint="Lowest sum insured (NPR)"
        >
          <Input
            id="advisor-coverage"
            type="number"
            inputMode="numeric"
            min={0}
            value={coverage}
            onChange={(e) => setCoverage(e.target.value)}
            placeholder="e.g. 1000000"
          />
        </Field>

        <div className="sm:col-span-2 lg:col-span-4">
          <Button type="submit" loading={state.phase === "loading"}>
            Find my plans
          </Button>
        </div>
      </form>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-12">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && <Alert variant="error">{state.message}</Alert>}

      {state.phase === "ready" && state.picks.length === 0 && (
        <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-10 text-center">
          <h3 className="font-display text-base font-semibold text-ink">
            No plans matched those criteria
          </h3>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
            Try widening your budget or clearing a filter and search again.
          </p>
        </div>
      )}

      {state.phase === "ready" && state.picks.length > 0 && (
        <div>
          <p className="text-sm text-muted">
            Ranked for you from {state.picks.length}{" "}
            {state.picks.length === 1 ? "plan" : "plans"} in our marketplace.
          </p>
          <div className="mt-4 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {state.picks.map((pick) => (
              <RecommendedPolicyCard key={pick.id} policy={pick} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/** A marketplace card topped with its match score and the reasons behind it. */
function RecommendedPolicyCard({ policy }: { policy: RecommendedPolicy }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="bg-success-50 text-success-800">
          {policy.match_score}% match
        </Badge>
        {policy.reasons.map((reason) => (
          <span
            key={reason}
            className="inline-flex items-center rounded-full border border-line bg-surface px-2.5 py-0.5 text-xs font-medium text-muted"
          >
            {reason}
          </span>
        ))}
      </div>
      <PolicyCard policy={policy} />
    </div>
  );
}
