import { useState } from 'react'
import { MapView } from './components/MapView'
import { WorksList } from './components/WorksList'
import { BudgetSimulator } from './components/BudgetSimulator'
import { BacktestPanel } from './components/BacktestPanel'

type Tab = 'map' | 'works' | 'budget' | 'backtest'

const TABS: { id: Tab; label: string }[] = [
  { id: 'works', label: 'Ranked Priorities' },
  { id: 'map', label: 'Map' },
  { id: 'budget', label: 'Budget Simulator' },
  { id: 'backtest', label: 'Backtest' },
]

function App() {
  const [tab, setTab] = useState<Tab>('works')

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
        <div className="mx-auto max-w-5xl px-4 py-4">
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">People's Priorities</h1>
          <p className="text-sm text-gray-500">Bagalkot constituency — data-driven development priorities</p>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 px-4">
          {TABS.map((t) => (
            <button
              key={t.id}
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

      <main>
        {tab === 'works' && <WorksList />}
        {tab === 'map' && <MapView />}
        {tab === 'budget' && <BudgetSimulator />}
        {tab === 'backtest' && <BacktestPanel />}
      </main>
    </div>
  )
}

export default App
