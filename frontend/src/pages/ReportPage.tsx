import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FileText, AlertTriangle, TrendingUp, Shield, MapPin } from 'lucide-react'
import { api } from '../api/client'
import { PageWrapper, PageHeader } from '../components/ui/PageWrapper'
import { MetricGrid, Metric } from '../components/ui/StatCard'
import { LoadingState, ErrorState } from '../components/ui/StateDisplays'
import type { ReactNode } from 'react'

function Section({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <motion.div
      className="card"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{ marginTop: 'var(--space-5)' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
        <div style={{ color: 'var(--color-text-tertiary)' }}>{icon}</div>
        <h3 className="section-title">{title}</h3>
      </div>
      {children}
    </motion.div>
  )
}

export function ReportPage() {
  const { data: summary, isLoading: sl, error: se, refetch: refetchS } = useQuery({
    queryKey: ['transparencySummary'],
    queryFn: api.transparencySummary,
  })
  const { data: backtest, isLoading: bl, error: be, refetch: refetchB } = useQuery({
    queryKey: ['backtest'],
    queryFn: api.backtest,
  })

  if (sl || bl) return <PageWrapper><LoadingState message="Generating intelligence report…" /></PageWrapper>
  if (se) return <PageWrapper><ErrorState message={(se as Error).message} onRetry={() => refetchS()} /></PageWrapper>
  if (be) return <PageWrapper><ErrorState message={(be as Error).message} onRetry={() => refetchB()} /></PageWrapper>
  if (!summary || !backtest) return null

  return (
    <PageWrapper>
      <PageHeader
        title="AI Intelligence Report"
        subtitle="Automated constituency analysis synthesized from citizen reports and infrastructure data"
      />

      {/* 1. Data summary */}
      <Section icon={<FileText size={17} />} title="Data summary">
        <MetricGrid style={{ background: 'transparent', border: 'none' }}>
          <Metric label="Citizen submissions" value={summary.total_submissions.toLocaleString('en-IN')} />
          <Metric label="Unique issues (post-dedup)" value={summary.total_issues.toLocaleString('en-IN')} />
          <Metric label="Dedup rate" value={`${Math.round(summary.dedup_rate * 100)}%`} />
          <Metric label="Themes covered" value={Object.keys(summary.theme_breakdown).length} />
        </MetricGrid>
        <p style={{ marginTop: 'var(--space-4)', fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
          {summary.total_submissions.toLocaleString('en-IN')} citizen submissions were de-duplicated into{' '}
          {summary.total_issues.toLocaleString('en-IN')} unique issues across{' '}
          {Object.keys(summary.theme_breakdown).length} development themes. The deduplication rate of{' '}
          {Math.round(summary.dedup_rate * 100)}% indicates the level of overlapping concerns among citizens.
        </p>
      </Section>

      {/* 2. Priority analysis */}
      <Section icon={<TrendingUp size={17} />} title="Priority analysis">
        <MetricGrid style={{ background: 'transparent', border: 'none' }}>
          <Metric label="Candidate works identified" value={summary.total_candidate_works.toLocaleString('en-IN')} />
          <Metric label="From citizen issues" value={summary.issue_based_works.toLocaleString('en-IN')} />
          <Metric label="Gap-only (silent need)" value={summary.gap_only_works.toLocaleString('en-IN')} />
        </MetricGrid>
        <p style={{ marginTop: 'var(--space-4)', fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
          Works are scored using a composite of citizen demand (corroboration), infrastructure gap severity, and population impact.
          {summary.gap_only_works > 0 && ` ${summary.gap_only_works} works were identified purely from infrastructure gap data — villages where objective need exists but no citizen has reported it.`}
        </p>
      </Section>

      {/* 3. Budget summary */}
      <Section icon={<Shield size={17} />} title="Budget allocation">
        <MetricGrid style={{ background: 'transparent', border: 'none' }}>
          <Metric label="Total budget" value={`₹${summary.budget.toLocaleString('en-IN')}`} />
          <Metric label="Works funded" value={summary.works_funded.toLocaleString('en-IN')} />
          <Metric label="Budget utilization" value={`${Math.round(summary.budget_used_pct * 100)}%`} />
        </MetricGrid>
      </Section>

      {/* 4. Backtest */}
      <Section icon={<TrendingUp size={17} />} title="Model validation (backtest)">
        <MetricGrid style={{ background: 'transparent', border: 'none', marginBottom: 'var(--space-4)' }}>
          <Metric label="Total villages analyzed" value={backtest.total_villages} />
          <Metric label="Historically funded" value={backtest.ground_truth_villages} />
          {backtest.cutoffs[0] && (
            <>
              <Metric label={`Precision @ top-${backtest.cutoffs[0].k}`} value={`${Math.round(backtest.cutoffs[0].precision * 100)}%`} />
              <Metric label={`Recall @ top-${backtest.cutoffs[0].k}`} value={`${Math.round(backtest.cutoffs[0].recall * 100)}%`} />
            </>
          )}
        </MetricGrid>
        <div className="callout callout-warning">
          <AlertTriangle size={16} />
          <div>
            <strong>Honest assessment:</strong> Precision sits close to the random-chance baseline at every cutoff —
            historical MPLADS allocation in Bagalkot only weakly correlates with objective infrastructure need.
            This is reported as measured, not adjusted to look better. The gap signal identifies genuine need,
            but past funding decisions were driven by factors outside this model.
          </div>
        </div>
      </Section>

      {/* 5. Key risks */}
      <Section icon={<MapPin size={17} />} title="Key risks & blind spots">
        <MetricGrid style={{ background: 'transparent', border: 'none', marginBottom: 'var(--space-4)' }}>
          <Metric label="Silent need villages" value={summary.silent_need_village_count} />
          <Metric label="Never addressed (high-gap)" value={backtest.never_addressed_high_gap_villages.length} />
          <Metric label="Village voice coverage" value={`${Math.round(summary.voice_coverage_pct * 100)}%`} />
        </MetricGrid>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
          {summary.silent_need_village_count} villages show high infrastructure gaps but have submitted zero citizen reports.
          These "silent need" areas risk being overlooked if decisions rely solely on citizen voice data.
          {backtest.never_addressed_high_gap_villages.length > 0 &&
            ` Additionally, ${backtest.never_addressed_high_gap_villages.length} high-gap villages have never received MPLADS funding historically.`}
        </p>
      </Section>
    </PageWrapper>
  )
}
