import type { Metadata } from "next";
import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = {
  title: "Create an account",
  description:
    "Create a free Bimaya account to compare and buy Life, Health, Vehicle and Travel insurance in Nepal.",
};

export default function RegisterPage() {
  return <RegisterForm />;
}
