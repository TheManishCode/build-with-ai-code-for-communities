import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Shield } from 'lucide-react'
import { api } from '../api/client'
import { PageWrapper, PageHeader } from '../components/ui/PageWrapper'
import { MetricGrid, Metric } from '../components/ui/StatCard'
import { LoadingState, ErrorState } from '../components/ui/StateDisplays'

const THEME_COLORS: Record<string, string> = {
  water: 'var(--theme-water)',
  road: 'var(--theme-road)',
  school: 'var(--theme-school)',
  health: 'var(--theme-health)',
  electricity: 'var(--theme-electricity)',
  sanitation: 'var(--theme-sanitation)',
}

export function TransparencyPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['transparencySummary'],
    queryFn: api.transparencySummary,
  })

  if (isLoading) return <PageWrapper><LoadingState message="Loading transparency data…" /></PageWrapper>
  if (error) return <PageWrapper><ErrorState message={(error as Error).message} onRetry={() => refetch()} /></PageWrapper>
  if (!data) return null

  const themeEntries = Object.entries(data.theme_breakdown).sort(([, a], [, b]) => b - a)
  const maxTheme = Math.max(...themeEntries.map(([, v]) => v))

  return (
    <PageWrapper>
      <PageHeader
        title="Transparency Dashboard"
        subtitle="A public accounting of what the platform has tracked — all figures computed live from the same data"
        actions={
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--text-xs)', color: 'var(--status-good)', fontWeight: 600 }}>
            <Shield size={13} /> Live data
          </div>
        }
      />

      <MetricGrid>
        <Metric label="Citizen submissions" value={data.total_submissions.toLocaleString('en-IN')} />
        <Metric
          label="Unique issues"
          value={data.total_issues.toLocaleString('en-IN')}
          sub={`${Math.round(data.dedup_rate * 100)}% dedup rate`}
        />
        <Metric
          label="Village coverage"
          value={`${data.villages_with_submissions} / ${data.total_villages}`}
          sub={`${Math.round(data.voice_coverage_pct * 100)}% have citizen voice`}
        />
        <Metric
          label="Silent need villages"
          value={data.silent_need_village_count.toLocaleString('en-IN')}
          sub="High gap, no voice"
        />
        <Metric
          label="Candidate works"
          value={data.total_candidate_works.toLocaleString('en-IN')}
          sub={`${data.issue_based_works} issue + ${data.gap_only_works} gap-only`}
        />
        <Metric
          label="Works funded"
          value={data.works_funded.toLocaleString('en-IN')}
          sub={`${Math.round(data.budget_used_pct * 100)}% of ₹${data.budget.toLocaleString('en-IN')}`}
        />
        <Metric
          label="Backtest precision @100"
          value={data.backtest_precision_at_100 != null ? `${Math.round(data.backtest_precision_at_100 * 100)}%` : '—'}
          sub="vs historically-funded villages"
        />
        <Metric
          label="Never addressed"
          value={data.backtest_never_addressed_count.toLocaleString('en-IN')}
          sub="high-gap, zero MPLADS history"
        />
      </MetricGrid>

      {/* Theme breakdown */}
      <motion.div
        className="card"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.3 }}
        style={{ marginTop: 'var(--space-6)' }}
      >
        <h3 className="section-title" style={{ marginBottom: 'var(--space-5)' }}>Reports by theme</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {themeEntries.map(([theme, count]) => (
            <div key={theme} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
              <span style={{
                width: 84,
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                color: 'var(--color-text-secondary)',
                textTransform: 'capitalize',
                flexShrink: 0,
              }}>
                {theme}
              </span>
              <div className="meter" style={{ flex: 1 }}>
                <div
                  className="meter-fill"
                  style={{
                    width: `${(count / maxTheme) * 100}%`,
                    background: THEME_COLORS[theme] || 'var(--theme-other)',
                  }}
                />
              </div>
              <span className="tabular-nums" style={{
                width: 32,
                textAlign: 'right',
                fontSize: 'var(--text-xs)',
                fontWeight: 600,
                color: 'var(--color-text-tertiary)',
              }}>
                {count}
              </span>
            </div>
          ))}
        </div>
      </motion.div>

      <p style={{
        marginTop: 'var(--space-6)',
        fontSize: 'var(--text-xs)',
        color: 'var(--color-text-muted)',
        textAlign: 'center',
        lineHeight: 'var(--leading-relaxed)',
      }}>
        All figures are computed live from the same pipeline data. Nothing is curated or filtered.
        This page exists to ensure the platform can be audited.
      </p>
    </PageWrapper>
  )
}
