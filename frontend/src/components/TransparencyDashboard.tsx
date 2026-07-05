import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function TransparencyDashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ['transparency'], queryFn: api.transparencySummary })

  if (isLoading) return <div className="p-6 text-gray-500">Loading constituency summary...</div>
  if (error) return <div className="p-6 text-red-600">Failed to load summary: {(error as Error).message}</div>
  if (!data) return null

  return (
    <div className="mx-auto max-w-4xl p-4">
      <h2 className="mb-1 text-lg font-semibold text-gray-900 dark:text-gray-100">Constituency Transparency Summary</h2>
      <p className="mb-4 text-sm text-gray-500">Bagalkot — a public accounting of what the platform has tracked so far.</p>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Citizen reports" value={data.total_submissions.toString()} />
        <Stat label="Deduplicated issues" value={data.total_issues.toString()} sub={`${Math.round(data.dedup_rate * 100)}% merged`} />
        <Stat label="Villages heard from" value={`${data.villages_with_submissions} / ${data.total_villages}`} sub={`${Math.round(data.voice_coverage_pct * 100)}% coverage`} />
        <Stat label="Silent-need villages" value={data.silent_need_village_count.toString()} sub="high gap, no voice" />
        <Stat label="Candidate works" value={data.total_candidate_works.toString()} sub={`${data.issue_based_works} from reports, ${data.gap_only_works} gap-only`} />
        <Stat label="Works funded" value={data.works_funded.toString()} sub={`${Math.round(data.budget_used_pct * 100)}% of budget used`} />
        <Stat
          label="Backtest precision @100"
          value={data.backtest_precision_at_100 != null ? `${Math.round(data.backtest_precision_at_100 * 100)}%` : '—'}
          sub={`vs ${data.backtest_ground_truth_villages} historically-funded villages`}
        />
        <Stat label="Never addressed" value={data.backtest_never_addressed_count.toString()} sub="high-gap, zero MPLADs history" />
      </div>

      <div className="mt-6 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Reports by theme</h3>
        <div className="flex flex-col gap-2">
          {Object.entries(data.theme_breakdown)
            .sort((a, b) => b[1] - a[1])
            .map(([theme, count]) => {
              const pct = data.total_issues ? (count / data.total_issues) * 100 : 0
              return (
                <div key={theme} className="flex items-center gap-2 text-sm">
                  <span className="w-24 shrink-0 text-gray-600 dark:text-gray-400">{theme}</span>
                  <div className="h-2 flex-1 rounded-full bg-gray-100 dark:bg-gray-700">
                    <div className="h-2 rounded-full bg-gray-900 dark:bg-gray-100" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="w-8 text-right tabular-nums text-gray-500">{count}</span>
                </div>
              )
            })}
        </div>
      </div>

      <p className="mt-4 text-xs text-gray-400">
        All figures are computed live from the same ranking, allocation, and backtest logic used elsewhere in this
        app — this page adds no new scoring, only aggregation.
      </p>
    </div>
  )
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 text-center dark:border-gray-700 dark:bg-gray-800">
      <div className="text-2xl font-bold tabular-nums text-gray-900 dark:text-gray-100">{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
      {sub && <div className="mt-1 text-xs text-gray-400">{sub}</div>}
    </div>
  )
}
