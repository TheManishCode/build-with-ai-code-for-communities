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
`.env` controls which backend it talks to. `src/components/` holds one component per
section of the app (ranked list, map, budget simulator, backtest, citizen status
lookup, transparency dashboard).
