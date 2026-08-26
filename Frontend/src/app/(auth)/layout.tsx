import Link from "next/link";
import { Logo } from "@/components/brand/logo";
import { BadgeCheckIcon, LockIcon, WalletIcon } from "@/components/icons";

const HIGHLIGHTS = [
  {
    Icon: BadgeCheckIcon,
    title: "Verified providers only",
    body: "Every insurer on Bimaya is reviewed and approved before a single policy goes live.",
  },
  {
    Icon: WalletIcon,
    title: "One place for every policy",
    body: "Life, Health, Vehicle and Travel cover — compared side by side, in plain language.",
  },
  {
    Icon: LockIcon,
    title: "Your details stay yours",
    body: "Bank-grade encryption, and we never sell your data to anyone.",
  },
];

/** Split layout used by every sign-in / sign-up screen. */
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col lg:grid lg:grid-cols-[1fr_minmax(0,29rem)] lg:flex-row-reverse">
      {/* Form column */}
      <main className="order-2 flex flex-1 flex-col justify-center px-4 py-10 sm:px-8 lg:order-1 lg:px-16">
        <div className="mx-auto w-full max-w-md">
          <Link
            href="/"
            aria-label="Bimaya home"
            className="mb-8 inline-flex lg:hidden"
          >
            <Logo height={32} priority />
          </Link>
          {children}
        </div>
      </main>

      {/* Brand column */}
      <aside className="order-1 flex flex-col justify-between gap-10 bg-brand-600 px-8 py-10 text-white lg:order-2 lg:px-12 lg:py-14">
        <Link href="/" aria-label="Bimaya home" className="inline-flex">
          <span className="rounded-lg bg-white px-3 py-2">
            <Logo height={28} priority />
          </span>
        </Link>

        <div className="hidden space-y-8 lg:block">
          <h2 className="font-display text-2xl font-semibold leading-snug">
            Online insurance,
            <br />
            made easy.
          </h2>

          <ul className="space-y-6">
            {HIGHLIGHTS.map(({ Icon, title, body }) => (
              <li key={title} className="flex gap-3.5">
                <Icon
                  className="mt-0.5 h-5 w-5 shrink-0 text-accent-300"
                  aria-hidden="true"
                />
                <div>
                  <p className="font-medium">{title}</p>
                  <p className="mt-1 text-sm leading-relaxed text-brand-100">
                    {body}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="hidden text-sm text-brand-200 lg:block">
          © {new Date().getFullYear()} Bimaya · Kathmandu, Nepal
        </p>
      </aside>
    </div>
  );
}
