import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '../api/client'
import { PageWrapper, PageHeader } from '../components/ui/PageWrapper'
import { MetricGrid, Metric } from '../components/ui/StatCard'
import { LoadingState, ErrorState } from '../components/ui/StateDisplays'

export function BacktestPage() {
  const [caveatsOpen, setCaveatsOpen] = useState(false)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['backtest'],
    queryFn: api.backtest,
  })

  if (isLoading) return <PageWrapper><LoadingState message="Loading backtest results…" /></PageWrapper>
  if (error) return <PageWrapper><ErrorState message={(error as Error).message} onRetry={() => refetch()} /></PageWrapper>
  if (!data) return null

  return (
    <PageWrapper>
      <PageHeader
        title="Model Backtest"
        subtitle="Would the objective gap signal have surfaced the villages where MPLADS money actually went?"
      />

      <MetricGrid>
        <Metric label="Total villages" value={data.total_villages.toString()} />
        <Metric label="Ground truth (funded)" value={data.ground_truth_villages.toString()} sub="historically received MPLADS" />
      </MetricGrid>

      {/* Cutoff table */}
      <motion.div
        className="card card-flush"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.3 }}
        style={{ marginTop: 'var(--space-5)' }}
      >
        <h3 className="section-title" style={{ padding: 'var(--space-5) var(--space-5) 0' }}>
          Precision at each cutoff
        </h3>
        <div style={{ overflow: 'auto', marginTop: 'var(--space-4)' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Top-K</th>
                <th>True positives</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>Random baseline</th>
              </tr>
            </thead>
            <tbody>
              {data.cutoffs.map((row) => (
                <tr key={row.k}>
                  <td style={{ fontWeight: 650, color: 'var(--color-text-primary)' }}>{row.k}</td>
                  <td>{row.true_positives}</td>
                  <td>
                    <span style={{
                      color: row.precision > row.random_baseline_precision * 1.5
                        ? 'var(--status-good)'
                        : 'var(--color-text-secondary)',
                      fontWeight: 600,
                    }}>
                      {Math.round(row.precision * 100)}%
                    </span>
                  </td>
                  <td>{Math.round(row.recall * 100)}%</td>
                  <td style={{ color: 'var(--color-text-muted)' }}>
                    {Math.round(row.random_baseline_precision * 100)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Honest assessment */}
      <div className="callout callout-warning" style={{ marginTop: 'var(--space-5)' }}>
        <AlertTriangle size={16} />
        <div>
          <strong>Honest assessment:</strong> Precision sits close to the random-chance baseline at every cutoff —
          historical MPLADS allocation in Bagalkot only weakly correlates with objective infrastructure need.
          Reported as measured, not adjusted to look better.
        </div>
      </div>

      {/* Never addressed */}
      {data.never_addressed_high_gap_villages.length > 0 && (
        <motion.div
          className="card card-flush"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.3 }}
          style={{ marginTop: 'var(--space-5)' }}
        >
          <h3 className="section-title" style={{ padding: 'var(--space-5) var(--space-5) var(--space-3)' }}>
            Never addressed — high gap villages
          </h3>
          <div style={{ padding: '0 var(--space-3) var(--space-3)' }}>
            {data.never_addressed_high_gap_villages.slice(0, 10).map((v) => (
              <div key={v.village_code} className="list-row">
                <span style={{ color: 'var(--color-text-secondary)' }}>{v.village_name}</span>
                <span className="tabular-nums" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-silent)', fontWeight: 600 }}>
                  Gap: {Math.round(v.overall_gap_percentile * 100)}%ile
                </span>
              </div>
            ))}
          </div>
          {data.never_addressed_high_gap_villages.length > 10 && (
            <p style={{ padding: '0 var(--space-5) var(--space-4)', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', textAlign: 'center' }}>
              …and {data.never_addressed_high_gap_villages.length - 10} more
            </p>
          )}
        </motion.div>
      )}

      {/* Caveats */}
      {data.caveats.length > 0 && (
        <div style={{ marginTop: 'var(--space-5)' }}>
          <button
            onClick={() => setCaveatsOpen(!caveatsOpen)}
            className="btn btn-ghost btn-sm"
            style={{ gap: 6 }}
          >
            {caveatsOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            Methodology & caveats ({data.caveats.length})
          </button>
          {caveatsOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="card"
              style={{ marginTop: 'var(--space-3)' }}
            >
              <ul style={{ listStyle: 'disc', paddingLeft: 'var(--space-5)', fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
                {data.caveats.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </motion.div>
          )}
        </div>
      )}
    </PageWrapper>
  )
}
