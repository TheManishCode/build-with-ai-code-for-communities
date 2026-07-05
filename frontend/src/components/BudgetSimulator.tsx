import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api } from '../api/client'

function formatRupees(n: number): string {
  return `Rs. ${n.toLocaleString('en-IN')}`
}

export function BudgetSimulator() {
  const { data: defaultAlloc } = useQuery({ queryKey: ['allocation-default'], queryFn: () => api.allocation() })
  const [budget, setBudget] = useState<number | null>(null)

  useEffect(() => {
    if (defaultAlloc && budget === null) setBudget(defaultAlloc.budget)
  }, [defaultAlloc, budget])

  const { data: alloc, isFetching } = useQuery({
    queryKey: ['allocation', budget],
    queryFn: () => api.allocation(budget!),
    enabled: budget !== null,
  })

  const maxBudget = defaultAlloc ? defaultAlloc.budget * 2 : 300_000_000

  return (
    <div className="mx-auto max-w-3xl p-4">
      <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Budget Simulator</h2>

      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-2 flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">MPLADs annual limit</label>
          <span className="text-lg font-bold tabular-nums text-gray-900 dark:text-gray-100">
            {budget != null ? formatRupees(budget) : '...'}
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={maxBudget}
          step={100000}
          value={budget ?? 0}
          onChange={(e) => setBudget(Number(e.target.value))}
          className="w-full accent-gray-900 dark:accent-gray-100"
        />
        {defaultAlloc && (
          <p className="mt-1 text-xs text-gray-400">
            Default is Bagalkot's real current (18th Lok Sabha) MPLADs allocated limit: {formatRupees(defaultAlloc.budget)}
          </p>
        )}

        {alloc && (
          <div className="mt-4 grid grid-cols-3 gap-3 border-t border-gray-100 pt-4 dark:border-gray-700">
            <Stat label="Works funded" value={alloc.n_works_selected.toString()} />
            <Stat label="Budget used" value={`${Math.round(alloc.budget_used_pct * 100)}%`} />
            <Stat label="Total priority value" value={alloc.total_value.toFixed(1)} />
          </div>
        )}
        {isFetching && <p className="mt-2 text-xs text-gray-400">Recomputing allocation...</p>}
      </div>

      {alloc && (
        <>
          <p className="mt-4 text-xs text-gray-500">{alloc.cost_heuristic_note}</p>
          <div className="mt-3 flex flex-col gap-2">
            {alloc.selected_works.slice(0, 15).map((w) => (
              <div
                key={w.work_id}
                className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
              >
                <div>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{w.village_name}</span>
                  <span className="ml-2 text-gray-500">({w.theme})</span>
                </div>
                <span className="tabular-nums text-gray-600 dark:text-gray-400">{formatRupees(w.cost)}</span>
              </div>
            ))}
            {alloc.selected_works.length > 15 && (
              <p className="text-xs text-gray-400">...and {alloc.selected_works.length - 15} more works funded.</p>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <div className="text-xl font-bold tabular-nums text-gray-900 dark:text-gray-100">{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  )
}
