import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Sidebar } from './components/layout/Sidebar'
import { MobileHeader } from './components/layout/MobileHeader'
import { ChatWidget } from './components/ChatWidget'
import { DashboardPage } from './pages/DashboardPage'
import { PrioritiesPage } from './pages/PrioritiesPage'
import { MapPage } from './pages/MapPage'
import { BudgetPage } from './pages/BudgetPage'
import { BacktestPage } from './pages/BacktestPage'
import { StatusPage } from './pages/StatusPage'
import { TransparencyPage } from './pages/TransparencyPage'
import { ReportPage } from './pages/ReportPage'
import { ReportIssuePage } from './pages/ReportIssuePage'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="app-shell">
      <div className="app-top-rule" aria-hidden="true" />
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Mobile overlay */}
      <div
        className={`mobile-overlay ${sidebarOpen ? 'open' : ''}`}
        onClick={() => setSidebarOpen(false)}
        role="presentation"
      />

      <div className="app-main">
        <MobileHeader onMenuToggle={() => setSidebarOpen((v) => !v)} />

        <main className="app-content">
          <div className="content-container">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/report" element={<ReportPage />} />
              <Route path="/priorities" element={<PrioritiesPage />} />
              <Route path="/map" element={<MapPage />} />
              <Route path="/budget" element={<BudgetPage />} />
              <Route path="/backtest" element={<BacktestPage />} />
              <Route path="/report-issue" element={<ReportIssuePage />} />
              <Route path="/status" element={<StatusPage />} />
              <Route path="/transparency" element={<TransparencyPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </main>
      </div>

      <ChatWidget />
    </div>
  )
}

export default App
