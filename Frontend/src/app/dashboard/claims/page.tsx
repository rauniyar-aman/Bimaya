import type { Metadata } from "next";
import { MyClaims } from "@/components/claims/my-claims";

export const metadata: Metadata = {
  title: "My claims",
  description:
    "The insurance claims you have filed through Bimaya, with status and settlement details.",
  robots: { index: false, follow: false },
};

export default function MyClaimsPage() {
  return <MyClaims />;
}
