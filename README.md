# Warehouse Frontend Assessment

Frontend application for warehouse inventory operations built with React, TypeScript, and Vite.

## Tech Stack

- React 19
- TypeScript
- Vite
- React Router
- Recharts (for Insights charts)
- CSS modules by feature folder (plain CSS files)

## Setup Instructions

1. Clone the repository.
2. Install dependencies:

```bash
npm install
```

3. Create/update `.env` in the project root with backend URL:

```env
BACKEND_URL=http://localhost:8000
```

Notes:
- In local dev, Vite proxy is used for `/api` requests.
- In production build mode, API calls use `BACKEND_URL`.

## How To Run The Application

Start development server:

```bash
npm run dev
```

Build for production:

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

## Project Structure

```text
.
├── public/                         # static files served as-is
│   ├── favicon.svg
│   └── icons.svg
├── src/
│   ├── component/                  # shared app-level UI
│   │   ├── Header.tsx              # top navigation
│   │   └── Header.css
│   ├── page/
│   │   ├── list/                   # inventory list page module
│   │   │   ├── api/                # backend adapters for dashboard/imports
│   │   │   ├── component/          # page-specific UI pieces
│   │   │   ├── form-validation/    # filter validation rules
│   │   │   ├── types/              # list domain types
│   │   │   ├── ListPage.tsx
│   │   │   ├── ListPage.css
│   │   │   └── index.ts
│   │   ├── item-details/           # item details page module (by SKU)
│   │   │   ├── index.tsx
│   │   │   └── ItemDetailsPage.css
│   │   └── insight/                # analytics/insight page module
│   │       ├── api/                # insights API adapter
│   │       ├── types/              # insights domain types
│   │       ├── index.tsx
│   │       └── InsightPage.css
│   ├── App.tsx                     # route definitions + app shell
│   ├── App.css
│   ├── main.tsx                    # React bootstrap + BrowserRouter
│   └── index.css                   # global styles and tokens
├── .env                            # local backend config (ignored)
├── package.json
├── vite.config.ts
└── README.md
```

## Architecture Overview

The app is organized by page/feature in `src/page`.

- `src/component`
- Contains shared app-level UI (`Header`).

- `src/page/list`
- Inventory list page.
- Includes modular components (`component/`), API clients (`api/`), types (`types/`), and filter validation (`form-validation/`).
- Handles filtering, sorting, pagination, CSV upload/import flow, and refresh after successful import.

- `src/page/item-details`
- SKU-based item details page (`/inventory/items/sku/:sku`).
- Renders stock levels and transaction history from backend.

- `src/page/insight`
- Insights/analytics page (`/insight`).
- Fetches `/api/v1/inventory/insights` and renders KPI cards and charts using Recharts.

- `src/App.tsx`
- App routing and layout shell with React Router.

