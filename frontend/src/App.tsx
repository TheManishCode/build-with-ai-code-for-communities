import { useState } from 'react'
import { MapView } from './components/MapView'
import { WorksList } from './components/WorksList'
import { BudgetSimulator } from './components/BudgetSimulator'
import { BacktestPanel } from './components/BacktestPanel'
import { CitizenStatusLookup } from './components/CitizenStatusLookup'
import { TransparencyDashboard } from './components/TransparencyDashboard'
import { SubmitReportForm } from './components/SubmitReportForm'

type Tab = 'report' | 'map' | 'works' | 'budget' | 'backtest' | 'status' | 'transparency'

const TABS: { id: Tab; label: string }[] = [
  { id: 'report', label: 'Report an Issue' },
  { id: 'works', label: 'Ranked Priorities' },
  { id: 'map', label: 'Map' },
  { id: 'budget', label: 'Budget Simulator' },
  { id: 'backtest', label: 'Backtest' },
  { id: 'status', label: 'Check My Report' },
  { id: 'transparency', label: 'Transparency' },
]

function App() {
  const [tab, setTab] = useState<Tab>('report')
  const [lastSubmissionId, setLastSubmissionId] = useState<number | undefined>(undefined)

  const handleViewStatus = (submissionId: number) => {
    setLastSubmissionId(submissionId)
    setTab('status')
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
        <div className="mx-auto max-w-5xl px-4 py-4">
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">People's Priorities</h1>
          <p className="text-sm text-gray-500">Bagalkot constituency — data-driven development priorities</p>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 px-4" role="tablist" aria-label="Sections">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              id={`tab-${t.id}`}
              aria-selected={tab === t.id}
              aria-controls={`panel-${t.id}`}
              onClick={() => setTab(t.id)}
              className={`rounded-t-md px-4 py-2 text-sm font-medium ${
                tab === t.id
                  ? 'border-b-2 border-gray-900 text-gray-900 dark:border-gray-100 dark:text-gray-100'
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main id={`panel-${tab}`} role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {tab === 'report' && <SubmitReportForm onViewStatus={handleViewStatus} />}
        {tab === 'works' && <WorksList />}
        {tab === 'map' && <MapView />}
        {tab === 'budget' && <BudgetSimulator />}
        {tab === 'backtest' && <BacktestPanel />}
        {tab === 'status' && <CitizenStatusLookup initialSubmissionId={lastSubmissionId} />}
        {tab === 'transparency' && <TransparencyDashboard />}
      </main>
    </div>
  )
}

export default App
