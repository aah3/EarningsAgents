---
name: frontend-component-and-ui
description: Workflow for creating and modifying Next.js 16 / React 19 components, dashboard views, WebSocket subscriptions, and API clients in web/.
---

# Frontend Component & UI Development Workflow

Follow this procedure when adding or modifying frontend UI components, pages, or API integrations in `web/`.

## 1. Component & Page Creation (`web/src/`)
1. Place pages inside App Router structure in `web/src/app/(auth)/` or `web/src/app/dashboard/`.
2. Follow Next.js 16 & React 19 conventions (Client Components declared with `'use client'`).
3. Use Tailwind CSS 4 for styling, matching the dark-mode modern financial aesthetic.

## 2. API & WebSocket Integration Invariants
1. Use backend client in `web/src/lib/api.ts` configured with `NEXT_PUBLIC_API_URL`.
2. For real-time prediction updates, subscribe to WebSocket channel via `NEXT_PUBLIC_WS_URL` connecting to `api/routers/websockets.py`.
3. **Ticker Sanitization & Caching Rule**:
   - Always sanitize and normalize ticker symbols before rendering UI components (e.g. upper-case, strip duplicate whitespace).
   - Cache redundant ticker metadata and prediction queries client-side to prevent unnecessary refetching.

## 3. Verification & Linting
1. Run local development server:
   ```bash
   cd web && npm run dev
   ```
2. Lint and build check:
   ```bash
   cd web && npm run lint && npm run build
   ```
