import { lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { SubmitReportForm } from './components/SubmitReportForm'

// Only the default landing view (the citizen report form) ships in the main bundle -- every
// other section is fetched on demand, since most first-time visitors on a data connection
// only ever need this one page. The map in particular pulls in Leaflet, which is heavy.
const WorksList = lazy(() => import('./components/WorksList').then((m) => ({ default: m.WorksList })))
const MapView = lazy(() => import('./components/MapView').then((m) => ({ default: m.MapView })))
const BudgetSimulator = lazy(() => import('./components/BudgetSimulator').then((m) => ({ default: m.BudgetSimulator })))
const BacktestPanel = lazy(() => import('./components/BacktestPanel').then((m) => ({ default: m.BacktestPanel })))
const CitizenStatusLookup = lazy(() =>
  import('./components/CitizenStatusLookup').then((m) => ({ default: m.CitizenStatusLookup })),
)
const TransparencyDashboard = lazy(() =>
  import('./components/TransparencyDashboard').then((m) => ({ default: m.TransparencyDashboard })),
)

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/report" replace />} />
        <Route path="report" element={<SubmitReportForm />} />
        <Route path="works" element={<WorksList />} />
        <Route path="map" element={<MapView />} />
        <Route path="budget" element={<BudgetSimulator />} />
        <Route path="backtest" element={<BacktestPanel />} />
        <Route path="status" element={<CitizenStatusLookup />} />
        <Route path="status/:submissionId" element={<CitizenStatusLookup />} />
        <Route path="transparency" element={<TransparencyDashboard />} />
        <Route path="*" element={<Navigate to="/report" replace />} />
      </Route>
    </Routes>
  )
}

export default App
