import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Map, Wallet, Shield, ArrowRight, ListOrdered } from 'lucide-react'
import { Link } from 'react-router-dom'
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

const QUICK_LINKS = [
  { to: '/priorities', label: 'Ranked Priorities', desc: 'AI-scored development works', icon: ListOrdered },
  { to: '/map', label: 'Constituency Map', desc: 'Geographic view of villages', icon: Map },
  { to: '/budget', label: 'Budget Simulator', desc: 'Explore allocation scenarios', icon: Wallet },
  { to: '/transparency', label: 'Transparency', desc: 'Public data accounting', icon: Shield },
]

export function DashboardPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['transparencySummary'],
    queryFn: api.transparencySummary,
  })

  if (isLoading) return <PageWrapper><LoadingState message="Loading constituency data…" /></PageWrapper>
  if (error) return <PageWrapper><ErrorState message={(error as Error).message} onRetry={() => refetch()} /></PageWrapper>
  if (!data) return null

  const themeEntries = Object.entries(data.theme_breakdown).sort(([, a], [, b]) => b - a)
  const maxTheme = Math.max(...themeEntries.map(([, v]) => v))

  return (
    <PageWrapper>
      <PageHeader
        title="Constituency Overview"
        subtitle="Data-driven development intelligence for Bagalkot, Karnataka"
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
          sub="High gap, no citizen reports"
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

      {/* Quick links */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))', gap: 'var(--space-4)', marginTop: 'var(--space-6)' }}>
        {QUICK_LINKS.map((link) => {
          const Icon = link.icon
          return (
            <Link key={link.to} to={link.to} style={{ textDecoration: 'none' }}>
              <div className="card card-interactive">
                <Icon size={18} style={{ color: 'var(--color-text-tertiary)', marginBottom: 'var(--space-3)' }} />
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 2 }}>
                  {link.label}
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', marginBottom: 'var(--space-3)' }}>
                  {link.desc}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', fontWeight: 600 }}>
                  Explore <ArrowRight size={12} />
                </div>
              </div>
            </Link>
          )
        })}
      </div>
    </PageWrapper>
  )
}
