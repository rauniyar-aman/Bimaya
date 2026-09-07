import { Suspense } from "react";
import { RequireAuth } from "@/components/auth/require-auth";
import { AdminNav } from "@/components/admin/admin-nav";
import { Container } from "@/components/layout/container";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { Spinner } from "@/components/ui/spinner";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Navbar />
      <Suspense
        fallback={
          <div className="flex flex-1 items-center justify-center py-24">
            <Spinner className="h-5 w-5 text-brand-500" />
          </div>
        }
      >
        <RequireAuth roles={["ADMIN"]}>
          <Container className="flex-1 py-8 lg:py-10">
            <header className="mb-6">
              <h1 className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
                Admin
              </h1>
              <p className="mt-1 text-sm text-muted">
                Onboard providers, verify customers, and keep the marketplace moving.
              </p>
            </header>
            <AdminNav />
            <div className="mt-8">{children}</div>
          </Container>
        </RequireAuth>
      </Suspense>
      <Footer />
    </>
  );
}
