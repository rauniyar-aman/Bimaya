import type { Metadata } from "next";
import { MyPolicies } from "@/components/purchases/my-policies";

export const metadata: Metadata = {
  title: "My policies",
  description: "The policies you have bought through Bimaya, with status and renewal dates.",
  robots: { index: false, follow: false },
};

export default function MyPoliciesPage() {
  return <MyPolicies />;
}
