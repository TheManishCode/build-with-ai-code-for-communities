import { Suspense } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { motion } from 'motion/react'
import { BarChart3, History, ListOrdered, Map as MapIcon, MessageSquarePlus, Search, Wallet } from 'lucide-react'
import { Mark } from '../ui/Mark'
import { Loading } from '../ui/PageState'
import { pageEnter } from '../../lib/motion'

const NAV: { to: string; label: string; icon: typeof MessageSquarePlus }[] = [
  { to: '/report', label: 'Report an Issue', icon: MessageSquarePlus },
  { to: '/works', label: 'Ranked Priorities', icon: ListOrdered },
  { to: '/map', label: 'Map', icon: MapIcon },
  { to: '/budget', label: 'Budget Simulator', icon: Wallet },
  { to: '/backtest', label: 'Backtest', icon: History },
  { to: '/status', label: 'Check My Report', icon: Search },
  { to: '/transparency', label: 'Transparency', icon: BarChart3 },
]

export function AppShell() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-stone-100 dark:bg-stone-950">
      <a
        href="#main"
        className="sr-only focus-visible:not-sr-only focus-visible:fixed focus-visible:left-4 focus-visible:top-4 focus-visible:z-50 focus-visible:rounded-md focus-visible:bg-accent-700 focus-visible:px-3 focus-visible:py-2 focus-visible:text-sm focus-visible:text-stone-50"
      >
        Skip to content
      </a>

      <header className="sticky top-0 z-30 border-b border-stone-200 bg-stone-100/95 backdrop-blur dark:border-stone-800 dark:bg-stone-950/95">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 pb-3 pt-4">
          <Mark size={30} className="shrink-0 text-gold-500 dark:text-gold-400" />
          <div className="min-w-0">
            <h1 className="font-display text-[1.05rem] font-medium leading-tight text-stone-900 dark:text-stone-50">
              People&rsquo;s Priorities
            </h1>
            <p className="text-[11px] font-medium uppercase leading-tight tracking-wide text-stone-500 dark:text-stone-400">
              Bagalkot Constituency &middot; Public Development Register
            </p>
          </div>
        </div>
        <nav
          className="scrollbar-none mx-auto flex max-w-5xl gap-5 overflow-x-auto px-4 pb-0"
          role="tablist"
          aria-label="Sections"
        >
          {NAV.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex shrink-0 items-center gap-1.5 border-b-2 py-2.5 text-[13px] font-medium transition-colors ${
                    isActive
                      ? 'border-accent-700 text-stone-900 dark:border-accent-400 dark:text-stone-50'
                      : 'border-transparent text-stone-500 hover:text-stone-800 dark:text-stone-400 dark:hover:text-stone-100'
                  }`
                }
              >
                <Icon size={14} aria-hidden="true" />
                {item.label}
              </NavLink>
            )
          })}
        </nav>
      </header>

      <motion.main
        id="main"
        key={location.pathname}
        initial="hidden"
        animate="visible"
        variants={pageEnter}
        className="pb-20 pt-8"
      >
        <Suspense fallback={<Loading label="Loading..." />}>
          <Outlet />
        </Suspense>
      </motion.main>
    </div>
  )
}
