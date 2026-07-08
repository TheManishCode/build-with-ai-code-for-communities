import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, ChevronDown } from 'lucide-react'
import { api } from '../api/client'
import { Loading, ErrorState, PageHeader } from './ui/PageState'
import { Card } from './ui/Card'
import { LineChart } from './ui/LineChart'

export function BacktestPanel() {
  const { data, isLoading, error } = useQuery({ queryKey: ['backtest'], queryFn: api.backtest })

  if (isLoading) return <Loading label="Loading backtest..." />
  if (error) return <ErrorState label={`Failed to load backtest: ${(error as Error).message}`} />
  if (!data) return null

  return (
    <div className="mx-auto max-w-3xl p-4">
      <PageHeader
        title="MPLADs Backtest — validating against the 17th Lok Sabha"
        subtitle={`Would the objective gap signal have surfaced the ${data.ground_truth_villages} villages where MPLADs money actually went (out of ${data.total_villages} total)?`}
      />

      <Card className="p-4">
        <LineChart
          xLabels={data.cutoffs.map((c) => c.k)}
          series={[
            { name: 'Precision', color: '#2a78d6', values: data.cutoffs.map((c) => c.precision) },
            { name: 'Recall', color: '#1baf7a', values: data.cutoffs.map((c) => c.recall) },
            { name: 'Random-chance baseline', color: '#898781', values: data.cutoffs.map((c) => c.random_baseline_precision) },
          ]}
        />
      </Card>

      <details className="mt-3 rounded-lg border border-neutral-200 dark:border-neutral-800">
        <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-2.5 text-sm font-medium text-neutral-700 dark:text-neutral-200">
          Full precision / recall table
          <ChevronDown size={15} className="text-neutral-400" aria-hidden="true" />
        </summary>
        <div className="overflow-hidden overflow-x-auto border-t border-neutral-200 dark:border-neutral-800">
          <table className="w-full text-sm">
            <thead className="bg-neutral-50 text-left text-neutral-500 dark:bg-neutral-900 dark:text-neutral-400">
              <tr>
                <th className="px-4 py-2 font-medium">Top-K villages</th>
                <th className="px-4 py-2 font-medium">Precision</th>
                <th className="px-4 py-2 font-medium">Recall</th>
                <th className="px-4 py-2 font-medium">Random-chance baseline</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {data.cutoffs.map((c) => (
                <tr key={c.k}>
                  <td className="px-4 py-2 font-medium text-neutral-900 dark:text-neutral-100">{c.k}</td>
                  <td className="px-4 py-2 tabular-nums text-neutral-700 dark:text-neutral-300">{Math.round(c.precision * 100)}%</td>
                  <td className="px-4 py-2 tabular-nums text-neutral-700 dark:text-neutral-300">{Math.round(c.recall * 100)}%</td>
                  <td className="px-4 py-2 tabular-nums text-neutral-500 dark:text-neutral-400">{Math.round(c.random_baseline_precision * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <div className="mt-4 flex items-start gap-2 rounded-lg bg-warning/15 p-3 text-xs text-amber-900 dark:bg-warning/10 dark:text-amber-200">
        <AlertTriangle size={15} className="mt-0.5 shrink-0" aria-hidden="true" />
        <p>
          <strong>Honest read:</strong> precision sits close to the random-chance baseline at every cutoff — historical
          MPLADs allocation in Bagalkot only weakly correlates with objective infrastructure need. Reported as measured,
          not adjusted to look better.
        </p>
      </div>

      <h3 className="mb-2 mt-6 text-sm font-semibold text-neutral-900 dark:text-neutral-50">
        Never addressed: {data.never_addressed_high_gap_villages.length} high-gap villages with zero MPLADs-funded work
      </h3>
      <div className="flex flex-col gap-1.5">
        {data.never_addressed_high_gap_villages.slice(0, 10).map((v) => (
          <div
            key={v.village_code}
            className="flex justify-between rounded-lg border border-neutral-100 bg-white px-3 py-1.5 text-sm dark:border-neutral-800 dark:bg-neutral-900"
          >
            <span className="text-neutral-900 dark:text-neutral-100">{v.village_name}</span>
            <span className="text-neutral-500 dark:text-neutral-400">gap percentile {Math.round(v.overall_gap_percentile * 100)}%</span>
          </div>
        ))}
      </div>

      <details className="mt-4">
        <summary className="cursor-pointer text-xs text-neutral-500 dark:text-neutral-400">Methodology &amp; caveats</summary>
        <ul className="mt-2 list-disc pl-5 text-xs text-neutral-500 dark:text-neutral-400">
          {data.caveats.map((c, i) => (
            <li key={i} className="mb-1">{c}</li>
          ))}
        </ul>
      </details>
    </div>
  )
}
