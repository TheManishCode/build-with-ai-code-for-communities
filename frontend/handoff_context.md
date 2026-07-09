# Civic Intelligence Platform — Frontend Rebuild Handoff

## Overview
We are in the process of completely rebuilding the frontend UI for the Civic Intelligence Platform (Bagalkot) into a professional, clean, fluid civic-tech product with a "liquid glass" aesthetic. 

Unfortunately, our parallel page-building subagents encountered rate limits, so the page components themselves have not been created yet. However, the foundational architecture, routing, design system, and shared components are fully in place.

## What Has Been Completed ✅

1.  **Dependencies Installed**
    *   `react-router-dom`, `framer-motion`, and `lucide-react` have been installed.
2.  **App Shell & Routing**
    *   `index.html`: Updated with proper fonts (`Inter`) and civic-themed meta tags.
    *   `src/main.tsx`: Wrapped the app in `<BrowserRouter>`.
    *   `src/App.tsx`: Rewritten to use `react-router-dom` with a `<Sidebar>` and a main content area containing the `<Routes>`.
3.  **Design System & CSS (`src/index.css`)**
    *   Created a comprehensive design system featuring a deep navy/slate base with saffron/teal accents.
    *   Added "glassmorphism" classes (`.glass-panel`, `.glass-panel-strong`).
    *   Defined typography, spacing, radii, and component-specific styles (stat cards, badges, buttons, inputs, tables).
    *   Added accessibility utilities (`.sr-only`, `.tabular-nums`).
4.  **Layout Components**
    *   `src/components/layout/Sidebar.tsx`: A responsive sidebar with animated active states (using `framer-motion` `layoutId`).
    *   `src/components/layout/MobileHeader.tsx`: A simple header for mobile views with a hamburger toggle.
5.  **Shared UI Components**
    *   `src/components/ui/PageWrapper.tsx`: Includes `<PageWrapper>` for page entry animations and `<PageHeader>`.
    *   `src/components/ui/StateDisplays.tsx`: Includes `<LoadingSkeleton>`, `<StatsSkeleton>`, `<Spinner>`, `<LoadingState>`, `<ErrorState>`, and `<EmptyState>`.
    *   `src/components/ui/StatCard.tsx`: A glass-panel stat card with hover effects.
6.  **Refactored Components**
    *   `src/components/DraftLetterModal.tsx`: Updated to use the new glass modal design and `framer-motion`.

---

## What Needs to be Done Next 🚀

The next step is to create the individual page components inside `src/pages/`. The previous attempt to do this in parallel failed due to API quota limits.

You need to create the following pages, adhering to the new design system:

### 1. `DashboardPage.tsx` (Route: `/`)
*   **Purpose**: High-level constituency overview.
*   **Data**: `api.transparencySummary`
*   **UI**: Use `<StatCard>`s for key metrics. Include a theme breakdown (horizontal bars). Quick links to other sections.

### 2. `ReportPage.tsx` (Route: `/report`)
*   **Purpose**: AI Report synthesis.
*   **Data**: `api.transparencySummary` and `api.backtest`
*   **UI**: Display key findings in `.glass-panel` sections (Data summary, Priority analysis, Budget summary, Backtest findings, Key risks).

### 3. `PrioritiesPage.tsx` (Route: `/priorities`)
*   **Purpose**: Ranked list of works.
*   **Data**: `api.works(limit)`
*   **UI**: A dropdown to select limit (10, 20, 50). A list of `WorkCard`s. Needs to integrate the `DraftLetterModal`.

### 4. `MapPage.tsx` (Route: `/map`)
*   **Purpose**: Geographic view.
*   **Data**: `api.boundary`
*   **UI**: Use `react-leaflet`. Dark themed tiles (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`). Markers colored by priority score. Toggle for "silent need" divergence overlay.

### 5. `BudgetPage.tsx` (Route: `/budget`)
*   **Purpose**: Budget Simulator.
*   **Data**: `api.allocation(budget)`, `api.works(500)`
*   **UI**: Range slider for budget. Stats grid for works funded/budget used. List of selected works. List of excluded works with expandable explanations (fetching `api.explain`).

### 6. `BacktestPage.tsx` (Route: `/backtest`)
*   **Purpose**: Model backtest validation.
*   **Data**: `api.backtest`
*   **UI**: Data table (`.data-table`) showing cutoffs, precision, recall. Callout warning (`.callout-warning`) for honest assessment. List of never addressed villages.

### 7. `StatusPage.tsx` (Route: `/status`)
*   **Purpose**: Check citizen report status.
*   **Data**: `api.citizenStatus(id)`
*   **UI**: Input field and submit button. Glass panel result card showing funding tier badge and detail grid.

### 8. `TransparencyPage.tsx` (Route: `/transparency`)
*   **Purpose**: Public accounting dashboard.
*   **Data**: `api.transparencySummary`
*   **UI**: Detailed stats grid and theme breakdown chart.

---

## Technical Guidelines for the Next AI/Developer

*   **Design System First**: Do not write custom inline styles or tailwind classes unless absolutely necessary. Rely on the classes defined in `src/index.css` (e.g., `.glass-panel`, `.badge-water`, `.btn-primary`).
*   **Animations**: Wrap page content in `<PageWrapper>`. Use `framer-motion` for list item staggering and modal entrances.
*   **Data Fetching**: Use `@tanstack/react-query` hooks and the existing client in `src/api/client.ts`. Use the loading/error components from `StateDisplays.tsx`.
*   **Icons**: Use `lucide-react` for all iconography.
*   **Imports**: Note that `tsconfig.app.json` has `verbatimModuleSyntax: true`. Ensure you use `import type { ... }` for type imports.
*   **Cleanup**: Once the pages are built, verify that no old components in `src/components/` (like the old `BudgetSimulator.tsx` or `WorksList.tsx`) are unused. If they are obsolete, delete them. Run `npm run lint` and `npm run build` to verify correctness.
