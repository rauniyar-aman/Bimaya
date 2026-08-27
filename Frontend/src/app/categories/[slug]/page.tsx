import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { CategoryIcon } from "@/components/marketplace/category-icon";
import { CompareBar } from "@/components/marketplace/compare-bar";
import { PolicyCard } from "@/components/marketplace/policy-card";
import { Container } from "@/components/layout/container";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { buttonVariants } from "@/components/ui/button";
import { ApiError, api, type InsuranceCategory } from "@/lib/api";

type Params = Promise<{ slug: string }>;

async function loadCategory(slug: string): Promise<InsuranceCategory> {
  try {
    return await api.categories.get(slug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Params;
}): Promise<Metadata> {
  const { slug } = await params;
  try {
    const category = await api.categories.get(slug);
    return {
      title: `${category.name} insurance`,
      description:
        category.description ||
        `Compare ${category.name} insurance plans on Bimaya.`,
    };
  } catch {
    return { title: "Category" };
  }
}

export default async function CategoryDetailPage({
  params,
}: {
  params: Params;
}) {
  const { slug } = await params;
  const category = await loadCategory(slug);

  // Best-effort: an empty list is a valid state, so a fetch failure here just
  // renders the header with no cards rather than 404-ing the whole page.
  const policies = await api.policies
    .list({ category: slug, page: 1 })
    .then((page) => page.results)
    .catch(() => []);

  return (
    <>
      <Navbar />
      <main className="flex-1">
        <section className="border-b border-line bg-gradient-to-b from-brand-50/60 to-white">
          <Container className="py-10 lg:py-14">
            <nav className="text-sm text-muted" aria-label="Breadcrumb">
              <Link href="/categories" className="hover:text-brand-600">
                Categories
              </Link>
              <span className="mx-1.5">/</span>
              <span className="text-ink">{category.name}</span>
            </nav>
            <div className="mt-4 flex items-center gap-3">
              <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                <CategoryIcon iconKey={category.icon} className="h-6 w-6" />
              </span>
              <h1 className="font-display text-3xl font-bold tracking-tight text-ink sm:text-4xl">
                {category.name} insurance
              </h1>
            </div>
            {category.description && (
              <p className="mt-3 max-w-2xl text-muted">{category.description}</p>
            )}
          </Container>
        </section>

        <Container className="py-10">
          {policies.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center">
              <h2 className="font-display text-lg font-semibold text-ink">
                No {category.name.toLowerCase()} plans yet
              </h2>
              <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
                Check back soon, or browse every plan on the marketplace.
              </p>
              <Link
                href="/policies"
                className={buttonVariants({
                  variant: "secondary",
                  size: "md",
                  className: "mt-5",
                })}
              >
                Browse all policies
              </Link>
            </div>
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {policies.map((policy) => (
                <PolicyCard key={policy.id} policy={policy} />
              ))}
            </div>
          )}
        </Container>
      </main>
      <Footer />
      <CompareBar />
    </>
  );
}
