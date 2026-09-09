import type { MetadataRoute } from "next";

/**
 * Web app manifest. Next serves this at `/manifest.webmanifest` and injects the
 * `<link rel="manifest">` automatically, so there's nothing to wire into the
 * layout. It gives the app an installable identity and the theme/background
 * colours used when it's launched from the home screen — and it's a prerequisite
 * for the browser push flow (see `components/notifications/push-toggle.tsx`).
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Bimaya — Online Insurance Made Easy",
    short_name: "Bimaya",
    description:
      "Nepal's digital insurance marketplace. Compare, buy and manage Life, Health, Vehicle and Travel insurance online.",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#1E5FA8",
    icons: [
      {
        src: "/bimaya-icon.png",
        sizes: "707x724",
        type: "image/png",
        purpose: "any",
      },
    ],
  };
}
