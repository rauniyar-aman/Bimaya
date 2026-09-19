import type { Metadata } from "next";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Container } from "@/components/layout/container";
import { ContactForm } from "@/components/contact/contact-form";

export const metadata: Metadata = {
  title: "Contact",
  description:
    "Get in touch with the Bimaya team. Questions about a policy, a purchase or a claim — send us a message and we'll get back to you.",
};

export default function ContactPage() {
  return (
    <>
      <Navbar />

      <main className="flex-1 bg-surface py-16 sm:py-20">
        <Container className="max-w-xl">
          <div className="mb-8">
            <h1 className="font-display text-3xl font-bold tracking-tight text-ink">
              Contact us
            </h1>
            <p className="mt-3 text-muted">
              Have a question about a policy, a purchase or a claim? Send us a
              message and the Bimaya team will get back to you. You can also
              reach us at{" "}
              <a
                href="mailto:support@bimaya.com"
                className="font-medium text-brand-ink underline-offset-4 hover:underline"
              >
                support@bimaya.com
              </a>
              .
            </p>
          </div>

          <div className="rounded-2xl border border-line bg-card p-6 shadow-sm sm:p-8">
            <ContactForm />
          </div>
        </Container>
      </main>

      <Footer />
    </>
  );
}
