"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { RequireAuth } from "@/components/auth/require-auth";
import { Container } from "@/components/layout/container";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { buttonVariants } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { CheckIcon, XIcon } from "@/components/icons";
import { api, type PaymentGateway } from "@/lib/api";

type State = { status: "loading" } | { status: "success" } | { status: "failed" };

function CallbackInner() {
  const searchParams = useSearchParams();
  const gatewayParam = (searchParams.get("gateway") ?? "").toUpperCase();
  const gateway: PaymentGateway | null =
    gatewayParam === "ESEWA" || gatewayParam === "KHALTI"
      ? (gatewayParam as PaymentGateway)
      : null;

  const [state, setState] = useState<State>({
    status: gateway ? "loading" : "failed",
  });

  useEffect(() => {
    if (!gateway) return;

    let cancelled = false;
    api.payments
      .confirm(gateway, searchParams)
      .then((result) => {
        if (!cancelled) {
          setState({ status: result.status === "SUCCESS" ? "success" : "failed" });
        }
      })
      .catch(() => {
        if (!cancelled) setState({ status: "failed" });
      });
    return () => {
      cancelled = true;
    };
  }, [gateway, searchParams]);

  if (state.status === "loading") {
    return (
      <main className="flex flex-1 items-center justify-center py-24">
        <Spinner className="h-6 w-6 text-brand-500" />
      </main>
    );
  }

  const success = state.status === "success";

  return (
    <main className="flex-1">
      <Container className="py-16">
        <div className="mx-auto max-w-lg rounded-2xl border border-line bg-white p-12 text-center shadow-sm">
          <span
            className={`mx-auto flex h-14 w-14 items-center justify-center rounded-full ${
              success
                ? "bg-success-50 text-success-600"
                : "bg-red-50 text-red-600"
            }`}
          >
            {success ? (
              <CheckIcon className="h-7 w-7" />
            ) : (
              <XIcon className="h-7 w-7" />
            )}
          </span>
          <h1 className="mt-4 font-display text-xl font-semibold text-ink">
            {success ? "Payment successful" : "Payment could not be confirmed"}
          </h1>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
            {success
              ? "Your policy is now active. You can find it in your dashboard."
              : "We could not confirm this payment. No charge was completed — please try again from checkout."}
          </p>
          <Link
            href={success ? "/dashboard" : "/policies"}
            className={buttonVariants({
              variant: "primary",
              size: "md",
              className: "mt-6",
            })}
          >
            {success ? "Go to dashboard" : "Browse policies"}
          </Link>
        </div>
      </Container>
    </main>
  );
}

export default function CheckoutCallbackPage() {
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
        <RequireAuth>
          <CallbackInner />
        </RequireAuth>
      </Suspense>
      <Footer />
    </>
  );
}
