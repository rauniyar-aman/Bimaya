# Bimaya

**Nepal's digital insurance marketplace — compare, buy and manage insurance online.**

Bimaya lets people discover and compare Life, Health, Vehicle and Travel insurance
plans from trusted providers across Nepal, buy them online in minutes, and manage
every policy in one place. Insurance providers list and manage their plans, and an
administrator reviews providers and policies before they go live.

> Status: **Phase 0 — foundation**. The branded frontend, design system and API
> foundation are in place. Authentication, policy listings, checkout and payments
> land in Phase 1 (see the [Roadmap](#roadmap)).

---

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Repository structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Getting started](#getting-started)
  - [1. Backend (Django REST API)](#1-backend-django-rest-api)
  - [2. Frontend (Next.js)](#2-frontend-nextjs)
- [Environment variables](#environment-variables)
- [API overview](#api-overview)
- [Roadmap](#roadmap)
- [License](#license)

---

## Features

**For customers**
- Browse and compare insurance plans by category, premium, coverage and term.
- Buy policies online with secure payment (eSewa and Khalti).
- Manage active and expired policies, download receipts and (later) file claims.

**For providers**
- Create and manage insurance plans.
- Track purchases and leads.

**For administrators**
- Review and approve providers and policies.
- Verify KYC and oversee users, transactions and platform data via the admin panel.

## Tech stack

| Layer      | Technology                                                        |
| ---------- | ----------------------------------------------------------------- |
| Frontend   | Next.js 16 (App Router, TypeScript), React 19, Tailwind CSS v4    |
| Backend    | Django 6 + Django REST Framework, SimpleJWT auth, drf-spectacular |
| Database   | PostgreSQL 18                                                     |
| Payments   | eSewa & Khalti (sandbox in development)                           |
| Docs       | OpenAPI schema + Swagger UI                                       |

The frontend and backend are decoupled and communicate over a versioned REST API
(`/api/v1`). CORS is locked to the frontend origin.

## Repository structure

```
Bimaya/
├── Backend/                 Django 6 + DRF REST API (runs on :8000)
│   ├── bimaya/              Project: settings, root URLs, ASGI/WSGI
│   ├── apps/
│   │   ├── core/            Shared base models, health endpoint
│   │   ├── accounts/        Custom user model, OTP
│   │   ├── providers/       Provider profiles & KYC        (Phase 1)
│   │   ├── policies/        Categories, policies, compare  (Phase 1)
│   │   ├── purchases/       Checkout & purchases           (Phase 1)
│   │   ├── payments/        eSewa / Khalti adapters        (Phase 1)
│   │   └── documents/       KYC uploads & PDF receipts     (Phase 1)
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example
├── Frontend/                Next.js app (runs on :3000)
│   ├── src/
│   │   ├── app/             App Router pages, layout, global styles
│   │   ├── components/      Design system, layout and brand components
│   │   └── lib/             Typed API client and helpers
│   ├── public/              Brand assets (logo, icon)
│   └── .env.local.example
└── README.md
```

## Prerequisites

- **Node.js** 20 or newer, with npm
- **Python** 3.12 or newer
- **PostgreSQL** 16 or newer, running locally

## Getting started

Clone the repository:

```bash
git clone https://github.com/rauniyar-aman/Bimaya.git
cd Bimaya
```

### 1. Backend (Django REST API)

Create and activate a virtual environment, then install dependencies:

```bash
cd Backend
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash);  use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

Create the database and role in PostgreSQL (run once, as the `postgres` superuser):

```bash
psql -U postgres -c "CREATE ROLE bimaya LOGIN PASSWORD 'bimaya_dev_pw';" -c "CREATE DATABASE bimaya OWNER bimaya;"
```

Configure environment variables and run migrations:

```bash
cp .env.example .env          # then edit .env if your DB credentials differ
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API is now available at `http://localhost:8000`:

- Health check: `http://localhost:8000/api/v1/health/`
- API docs (Swagger UI): `http://localhost:8000/api/v1/docs/`
- Admin panel: `http://localhost:8000/admin/`

### 2. Frontend (Next.js)

In a separate terminal:

```bash
cd Frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open `http://localhost:3000`. With the backend running, the homepage footer shows a
live "API connected" status from the health endpoint.

## Environment variables

**Backend** (`Backend/.env`, copied from `.env.example`):

| Variable                | Description                                       |
| ----------------------- | ------------------------------------------------- |
| `DJANGO_SECRET_KEY`     | Django secret key (use a long random string)      |
| `DJANGO_DEBUG`          | `True` in development, `False` in production      |
| `DJANGO_ALLOWED_HOSTS`  | Comma-separated allowed hosts                     |
| `DATABASE_URL`          | `postgres://USER:PASSWORD@HOST:PORT/DBNAME`       |
| `FRONTEND_URL`          | Frontend origin, used for CORS                    |
| `CORS_ALLOWED_ORIGINS`  | Comma-separated allowed origins                   |
| `EMAIL_BACKEND`         | Django email backend (console in development)     |

**Frontend** (`Frontend/.env.local`, copied from `.env.local.example`):

| Variable                     | Description                          |
| ---------------------------- | ------------------------------------ |
| `NEXT_PUBLIC_API_BASE_URL`   | Base URL of the backend API          |
| `NEXT_PUBLIC_SITE_URL`       | Public site URL (used for metadata)  |

Real values — production secret key, live eSewa/Khalti merchant credentials and an
SMS gateway for OTP — are supplied through environment variables at deploy time and
are never committed.

## API overview

All endpoints are served under `/api/v1/`.

| Endpoint            | Description                                 |
| ------------------- | ------------------------------------------- |
| `GET /health/`      | Service health check                        |
| `GET /schema/`      | OpenAPI schema                              |
| `GET /docs/`        | Swagger UI                                  |

Authentication (JWT), categories, policies, purchases and payments endpoints are
added in Phase 1.

## Roadmap

- **Phase 0 — Foundation** *(current)*: monorepo, backend project + apps skeleton,
  PostgreSQL, DRF + JWT + CORS + OpenAPI, custom user model, health endpoint; Next.js
  app with brand theme, design system, layout and typed API client.
- **Phase 1 — MVP**: full authentication (register, OTP, login, refresh, reset,
  role-based access); categories and policies (provider management, public
  list/search/filter/compare); purchases, payments (eSewa/Khalti sandbox) and PDF
  receipts; KYC upload; admin approvals; seed data and tests.
- **Phase 2**: claims, notifications (email/SMS/in-app), provider analytics and
  custom admin dashboards.
- **Phase 3**: plan recommendations, chatbot, Nepali/English localisation and a
  mobile app.

## License

© 2026 Bimaya. All rights reserved.
