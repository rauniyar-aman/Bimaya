"use client";

import { use } from "react";
import { ClaimCreate } from "@/components/claims/claim-create";

type SearchParams = Promise<{ purchase?: string | string[] }>;

/** A `?purchase=<id>` deep link preselects that policy on the claim form. */
function parsePurchaseId(
  raw: string | string[] | undefined,
): number | undefined {
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (!value) return undefined;
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : undefined;
}

export default function NewClaimPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const sp = use(searchParams);
  return <ClaimCreate purchaseId={parsePurchaseId(sp.purchase)} />;
}
