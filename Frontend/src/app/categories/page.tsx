import type { Metadata } from "next";
import Link from "next/link";
import { CategoryIcon } from "@/components/marketplace/category-icon";
import { Container } from "@/components/layout/container";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { Alert } from "@/components/ui/alert";
import { ArrowRightIcon } from "@/components/icons";
import { api, type InsuranceCategory } from "@/lib/api";

export const metadata: Metadata = {
  title: "Insurance categories",
  description:
    "Explore Life, Health, Vehicle and Travel insurance categories on Bimaya.",
};

export default async function CategoriesPage() {
  let categories: InsuranceCategory[] = [];
  let failed = false;
  try {
    categories = await api.categories.list();
  } catch {
    failed = true;
  }

  return (
    <>
      <Navbar />
      <main className="flex-1">
        <section className="border-b border-line bg-gradient-to-b from-brand-50/60 to-white">
          <Container className="py-10 lg:py-14">
            <h1 className="font-display text-3xl font-bold tracking-tight text-ink sm:text-4xl">
              Insurance categories
            </h1>
            <p className="mt-2 max-w-2xl text-muted">
              Whatever you need to protect, find the right cover from providers
              across Nepal.
            </p>
          </Container>
        </section>

        <Container className="py-10">
          {failed ? (
            <Alert variant="error">
              We could not load categories right now. Please try again shortly.
            </Alert>
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {categories.map((category) => {
                return (
                  <Link
                    key={category.slug}
                    href={`/categories/${category.slug}`}
                    className="group rounded-2xl border border-line bg-white p-6 shadow-sm transition-all hover:-translate-y-1 hover:border-brand-200 hover:shadow-md"
                  >
                    <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                      <CategoryIcon iconKey={category.icon} className="h-6 w-6" />
                    </span>
                    <h2 className="mt-4 font-display text-lg font-semibold text-ink">
                      {category.name}
                    </h2>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted">
                      {category.description ||
                        `Compare ${category.name.toLowerCase()} insurance plans.`}
                    </p>
                    <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-brand-600">
                      {category.policy_count}{" "}
                      {category.policy_count === 1 ? "plan" : "plans"}
                      <ArrowRightIcon className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                    </span>
                  </Link>
                );
              })}
            </div>
          )}
        </Container>
      </main>
      <Footer />
    </>
  );
}
