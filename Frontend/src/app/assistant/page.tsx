import type { Metadata } from "next";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Container } from "@/components/layout/container";
import { RecommendPanel } from "@/components/assistant/recommend-panel";
import { ChatIcon, ShieldCheckIcon } from "@/components/icons";

export const metadata: Metadata = {
  title: "AI advisor",
  description:
    "Tell Bimaya what you need and get insurance plans ranked for your budget, age and cover — then ask the advisor any insurance question.",
};

export default function AssistantPage() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        <Container className="py-8 lg:py-12">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
              <ShieldCheckIcon className="h-3.5 w-3.5" />
              Personalised, and always from real listed plans
            </span>
            <h1 className="mt-4 font-display text-3xl font-bold tracking-tight text-ink sm:text-4xl">
              Find the right cover
            </h1>
            <p className="mt-2 text-muted">
              Tell us a little about what you&apos;re after and we&apos;ll rank the
              plans in our marketplace for you. Every premium and coverage figure
              comes straight from the listed policy — nothing is made up.
            </p>
          </div>

          <div className="mt-8">
            <RecommendPanel />
          </div>

          <div className="mt-12 flex items-start gap-3 rounded-2xl border border-line bg-surface/60 p-5">
            <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
              <ChatIcon className="h-5 w-5" />
            </span>
            <div>
              <h2 className="font-display text-base font-semibold text-ink">
                Have a question?
              </h2>
              <p className="mt-1 text-sm text-muted">
                Open the advisor from the button in the bottom corner to ask about
                terms, coverage or how a plan works. Please don&apos;t share ID or
                health numbers in the chat.
              </p>
            </div>
          </div>
        </Container>
      </main>
      <Footer />
    </>
  );
}
