import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function BacktestPanel() {
  const { data, isLoading, error } = useQuery({ queryKey: ['backtest'], queryFn: api.backtest })

  if (isLoading) return <div className="p-6 text-gray-500">Loading backtest...</div>
  if (error) return <div className="p-6 text-red-600">Failed to load backtest: {(error as Error).message}</div>
  if (!data) return null

  return (
    <div className="mx-auto max-w-3xl p-4">
      <h2 className="mb-1 text-lg font-semibold text-gray-900 dark:text-gray-100">
        MPLADs Backtest — validating against the 17th Lok Sabha
      </h2>
      <p className="mb-4 text-sm text-gray-500">
        Would the objective gap signal have surfaced the {data.ground_truth_villages} villages where MPLADs money
        actually went (out of {data.total_villages} total)?
      </p>

      <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
        <table className="w-full text-sm">
          <thead className="bg-gray-100 text-left text-gray-600 dark:bg-gray-800 dark:text-gray-300">
            <tr>
              <th className="px-3 py-2">Top-K villages</th>
              <th className="px-3 py-2">Precision</th>
              <th className="px-3 py-2">Recall</th>
              <th className="px-3 py-2">Random-chance baseline</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white dark:divide-gray-700 dark:bg-gray-800">
            {data.cutoffs.map((c) => (
              <tr key={c.k}>
                <td className="px-3 py-2 font-medium text-gray-900 dark:text-gray-100">{c.k}</td>
                <td className="px-3 py-2 tabular-nums">{Math.round(c.precision * 100)}%</td>
                <td className="px-3 py-2 tabular-nums">{Math.round(c.recall * 100)}%</td>
                <td className="px-3 py-2 tabular-nums text-gray-500">{Math.round(c.random_baseline_precision * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 rounded-md bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
        <strong>Honest read:</strong> precision sits close to the random-chance baseline at every cutoff — historical
        MPLADs allocation in Bagalkot only weakly correlates with objective infrastructure need. Reported as measured,
        not adjusted to look better.
      </div>

      <h3 className="mt-6 mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
        Never addressed: {data.never_addressed_high_gap_villages.length} high-gap villages with zero MPLADs-funded work
      </h3>
      <div className="flex flex-col gap-1">
        {data.never_addressed_high_gap_villages.slice(0, 10).map((v) => (
          <div key={v.village_code} className="flex justify-between rounded-md border border-gray-100 bg-white px-3 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-800">
            <span className="text-gray-900 dark:text-gray-100">{v.village_name}</span>
            <span className="text-gray-500">gap percentile {Math.round(v.overall_gap_percentile * 100)}%</span>
          </div>
        ))}
      </div>

      <details className="mt-4">
        <summary className="cursor-pointer text-xs text-gray-500">Methodology &amp; caveats</summary>
        <ul className="mt-2 list-disc pl-5 text-xs text-gray-500">
          {data.caveats.map((c, i) => (
            <li key={i} className="mb-1">{c}</li>
          ))}
        </ul>
      </details>
    </div>
  )
}
