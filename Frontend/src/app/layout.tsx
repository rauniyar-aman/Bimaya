import type { Metadata, Viewport } from "next";
import { Inter, Sora } from "next/font/google";
import { AuthProvider } from "@/components/auth/auth-provider";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-sora",
  weight: ["500", "600", "700", "800"],
  display: "swap",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

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
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${sora.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
