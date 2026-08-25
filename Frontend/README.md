# Bimaya — Frontend

The web frontend for Bimaya, Nepal's digital insurance marketplace. Built with
Next.js 16 (App Router), React 19, TypeScript and Tailwind CSS v4.

## Getting started

```bash
npm install
cp .env.local.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). With the backend running, the
footer shows a live status from the API health endpoint.

## Scripts

| Command         | Description                          |
| --------------- | ------------------------------------ |
| `npm run dev`   | Start the development server         |
| `npm run build` | Create a production build            |
| `npm run start` | Serve the production build           |
| `npm run lint`  | Run ESLint                           |

## Environment variables

Copy `.env.local.example` to `.env.local`:

| Variable                   | Description                         |
| -------------------------- | ----------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL` | Base URL of the backend API         |
| `NEXT_PUBLIC_SITE_URL`     | Public site URL (used for metadata) |

## Structure

```
src/
├── app/          App Router pages, root layout and global styles
├── components/   Design system, layout, brand and site components
└── lib/          Typed API client and helpers
```

See the [root README](../README.md) for full project setup, including the backend.
