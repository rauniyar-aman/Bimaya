"use client";

import { use } from "react";
import { PurchaseDetail } from "@/components/purchases/purchase-detail";

type Params = Promise<{ id: string }>;

export default function PurchaseDetailPage({ params }: { params: Params }) {
  const { id } = use(params);
  return <PurchaseDetail id={id} />;
}
