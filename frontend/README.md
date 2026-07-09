# Frontend

React 19 + Vite + TanStack Query + Tailwind v4 + Leaflet. See the [project
README](../README.md) for the full picture and the API this talks to.

```bash
npm install
npm run dev       # http://localhost:5173, requires the backend running (see ../README.md)
npm test          # vitest
npm run lint      # oxlint
npm run build     # tsc -b && vite build
```

`src/api/client.ts` is the single point of contact with the backend; `VITE_API_BASE` in
`.env` controls which backend it talks to. `src/pages/` holds one page per route
(dashboard, AI report, ranked priorities, map, budget simulator, backtest, report an
issue, check my report, transparency); `src/components/ui/` holds the shared primitives
(`PageWrapper`/`PageHeader`, `Metric`/`MetricGrid`, loading/error/empty states) every page
is built from, and `src/index.css`'s design tokens section (near-black flat surfaces, one
reserved accent, a fixed categorical palette for theme charts) is where to change a color
-- not in individual components. Icons are `lucide-react`.
