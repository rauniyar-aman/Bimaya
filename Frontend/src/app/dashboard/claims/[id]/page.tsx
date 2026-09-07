"use client";

import { use } from "react";
import { ClaimDetail } from "@/components/claims/claim-detail";

type Params = Promise<{ id: string }>;

export default function ClaimDetailPage({ params }: { params: Params }) {
  const { id } = use(params);
  return <ClaimDetail id={id} />;
}
