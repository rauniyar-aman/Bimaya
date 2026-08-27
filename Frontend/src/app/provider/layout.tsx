import { Suspense } from "react";
import { RequireAuth } from "@/components/auth/require-auth";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { Spinner } from "@/components/ui/spinner";

export default function ProviderLayout({
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
        <RequireAuth roles={["PROVIDER"]}>{children}</RequireAuth>
      </Suspense>
      <Footer />
    </>
  );
}
