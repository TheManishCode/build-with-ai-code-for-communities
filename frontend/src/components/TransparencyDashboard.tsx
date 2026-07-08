import { useQuery } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, EyeOff, GitMerge, ListChecks, MapPin, MessageSquare, Target } from 'lucide-react'
import { api } from '../api/client'
import { Loading, ErrorState, PageHeader } from './ui/PageState'
import { StatTile } from './ui/StatTile'
import { Card } from './ui/Card'
import { BarChart } from './ui/BarChart'
import { InfoTooltip } from './ui/InfoTooltip'
import { themeColor } from '../theme'

export function TransparencyDashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ['transparency'], queryFn: api.transparencySummary })

  if (isLoading) return <Loading label="Loading constituency summary..." />
  if (error) return <ErrorState label={`Failed to load summary: ${(error as Error).message}`} />
  if (!data) return null

  const themeData = Object.entries(data.theme_breakdown)
    .sort((a, b) => b[1] - a[1])
    .map(([theme, count]) => ({
      label: theme,
      value: count,
      color: themeColor(theme).swatch,
      formattedValue: count.toLocaleString(),
    }))

  return (
    <div className="mx-auto max-w-4xl p-4">
      <PageHeader
        title="Constituency Transparency Summary"
        subtitle="Bagalkot — a public accounting of what the platform has tracked so far."
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile icon={<MessageSquare size={14} />} label="Citizen reports" value={data.total_submissions.toString()} />
        <StatTile
          icon={<GitMerge size={14} />}
          label="Deduplicated issues"
          value={data.total_issues.toString()}
          sub={`${Math.round(data.dedup_rate * 100)}% merged`}
        />
        <StatTile
          icon={<MapPin size={14} />}
          label="Villages heard from"
          value={`${data.villages_with_submissions} / ${data.total_villages}`}
          sub={`${Math.round(data.voice_coverage_pct * 100)}% coverage`}
        />
        <StatTile
          icon={<EyeOff size={14} />}
          label="Silent-need villages"
          value={data.silent_need_village_count.toString()}
          sub="high gap, no voice"
        />
        <StatTile
          icon={<ListChecks size={14} />}
          label="Candidate works"
          value={data.total_candidate_works.toString()}
          sub={`${data.issue_based_works} from reports, ${data.gap_only_works} gap-only`}
        />
        <StatTile
          icon={<CheckCircle2 size={14} />}
          label="Works funded"
          value={data.works_funded.toString()}
          sub={`${Math.round(data.budget_used_pct * 100)}% of budget used`}
        />
        <StatTile
          icon={<Target size={14} />}
          label="Backtest precision @100"
          value={data.backtest_precision_at_100 != null ? `${Math.round(data.backtest_precision_at_100 * 100)}%` : '—'}
          sub={`vs ${data.backtest_ground_truth_villages} historically-funded villages`}
        />
        <StatTile
          icon={<AlertCircle size={14} />}
          label="Never addressed"
          value={data.backtest_never_addressed_count.toString()}
          sub="high-gap, zero MPLADs history"
        />
      </div>

      <Card className="mt-6 p-4">
        <div className="mb-3 flex items-center gap-1.5">
          <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">Reports by theme</h3>
          <InfoTooltip label="How theme is assigned">
            Each report is machine-classified into one of 7 themes by keyword-occurrence scoring
            against its translated text -- transparent and re-checkable, not a black box.
          </InfoTooltip>
        </div>
        <BarChart data={themeData} />
      </Card>

      <p className="mt-4 text-xs text-neutral-400 dark:text-neutral-500">
        All figures are computed live from the same ranking, allocation, and backtest logic used elsewhere in this
        app — this page adds no new scoring, only aggregation.
      </p>
    </div>
  )
}
