import type { Metadata, Viewport } from "next";
import { Fraunces, Mukta } from "next/font/google";
import { AuthProvider } from "@/components/auth/auth-provider";
import { ChatWidget } from "@/components/assistant/chat-widget";
import { ThemeProvider } from "@/components/theme/theme-provider";
import "./globals.css";

// Text face. Mukta ships Devanagari and Latin in one family, so the Nepali
// translation adds "devanagari" to `subsets` here rather than a second font —
// until then we only pay for the Latin glyphs we actually render.
const mukta = Mukta({
  subsets: ["latin"],
  variable: "--font-mukta",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

// Display face, for headings and money. The `opsz` axis lets one family cover a
// 12px label and a 56px rupee figure, optically sized by the browser at each.
const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  axes: ["opsz"],
  display: "swap",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

// Runs before first paint to set the theme class, so there is no flash of the
// wrong theme before React hydrates. Mirrors the logic in ThemeProvider and
// reads the same localStorage key.
const THEME_SCRIPT = `(function(){try{var k="bimaya-theme",s=localStorage.getItem(k),d=s==="dark"||((s==="system"||!s)&&window.matchMedia("(prefers-color-scheme: dark)").matches),e=document.documentElement;e.classList.toggle("dark",d);e.style.colorScheme=d?"dark":"light";}catch(e){}})();`;

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Bimaya — Online Insurance Made Easy",
    template: "%s · Bimaya",
  },
  description:
    "Bimaya is Nepal's digital insurance marketplace. Compare, buy and manage Life, Health, Vehicle and Travel insurance online — simple, transparent and secure.",
  keywords: [
    "Bimaya",
    "insurance Nepal",
    "online insurance",
    "compare insurance",
    "health insurance",
    "life insurance",
    "vehicle insurance",
    "travel insurance",
  ],
  openGraph: {
    type: "website",
    siteName: "Bimaya",
    title: "Bimaya — Online Insurance Made Easy",
    description:
      "Compare, buy and manage insurance online across Nepal — Life, Health, Vehicle and Travel.",
    url: siteUrl,
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1626" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${mukta.variable} ${fraunces.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
        <ThemeProvider>
          <AuthProvider>
            {children}
            <ChatWidget />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
