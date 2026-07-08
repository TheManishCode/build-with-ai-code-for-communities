import { useState } from 'react'
import { BarChart3, History, ListOrdered, Map as MapIcon, MessageSquarePlus, Search, Wallet } from 'lucide-react'
import { MapView } from './components/MapView'
import { WorksList } from './components/WorksList'
import { BudgetSimulator } from './components/BudgetSimulator'
import { BacktestPanel } from './components/BacktestPanel'
import { CitizenStatusLookup } from './components/CitizenStatusLookup'
import { TransparencyDashboard } from './components/TransparencyDashboard'
import { SubmitReportForm } from './components/SubmitReportForm'

type Tab = 'report' | 'map' | 'works' | 'budget' | 'backtest' | 'status' | 'transparency'

const TABS: { id: Tab; label: string; icon: typeof MessageSquarePlus }[] = [
  { id: 'report', label: 'Report an Issue', icon: MessageSquarePlus },
  { id: 'works', label: 'Ranked Priorities', icon: ListOrdered },
  { id: 'map', label: 'Map', icon: MapIcon },
  { id: 'budget', label: 'Budget Simulator', icon: Wallet },
  { id: 'backtest', label: 'Backtest', icon: History },
  { id: 'status', label: 'Check My Report', icon: Search },
  { id: 'transparency', label: 'Transparency', icon: BarChart3 },
]

function App() {
  const [tab, setTab] = useState<Tab>('report')
  const [lastSubmissionId, setLastSubmissionId] = useState<number | undefined>(undefined)

  const handleViewStatus = (submissionId: number) => {
    setLastSubmissionId(submissionId)
    setTab('status')
  }

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <header className="sticky top-0 z-30 border-b border-neutral-200 bg-white/90 backdrop-blur dark:border-neutral-800 dark:bg-neutral-950/90">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3.5">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-500 font-semibold text-white">
            PP
          </div>
          <div>
            <h1 className="text-base font-semibold leading-tight text-neutral-900 dark:text-neutral-50">People's Priorities</h1>
            <p className="text-xs leading-tight text-neutral-500 dark:text-neutral-400">
              Bagalkot constituency — data-driven development priorities
            </p>
          </div>
        </div>
        <nav
          className="scrollbar-none mx-auto flex max-w-6xl gap-1 overflow-x-auto px-4 pb-2"
          role="tablist"
          aria-label="Sections"
        >
          {TABS.map((t) => {
            const Icon = t.icon
            const active = tab === t.id
            return (
              <button
                key={t.id}
                role="tab"
                id={`tab-${t.id}`}
                aria-selected={active}
                aria-controls={`panel-${t.id}`}
                onClick={() => setTab(t.id)}
                className={`flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-200'
                    : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-800 dark:text-neutral-400 dark:hover:bg-neutral-900 dark:hover:text-neutral-100'
                }`}
              >
                <Icon size={15} aria-hidden="true" />
                {t.label}
              </button>
            )
          })}
        </nav>
      </header>

      <main id={`panel-${tab}`} role="tabpanel" aria-labelledby={`tab-${tab}`} className="pb-16 pt-6">
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
