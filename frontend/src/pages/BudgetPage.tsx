import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, XCircle, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react'
import { api } from '../api/client'
import type { BudgetEvidenceResponse, ExplanationResponse } from '../api/types'
import { PageWrapper, PageHeader } from '../components/ui/PageWrapper'
import { MetricGrid, Metric } from '../components/ui/StatCard'
import { LoadingState, ErrorState, Spinner } from '../components/ui/StateDisplays'

function BudgetEvidencePanel({ evidence }: { evidence: BudgetEvidenceResponse }) {
  return (
    <div style={{ marginTop: 'var(--space-3)', paddingTop: 'var(--space-3)', borderTop: '1px solid var(--color-border-default)' }}>
      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
        {evidence.narrative}
      </p>
      {evidence.comparables.length > 0 && (
        <ul style={{ marginTop: 'var(--space-2)', paddingLeft: 'var(--space-5)', listStyle: 'disc' }}>
          {evidence.comparables.map((c, i) => (
            <li key={i} style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', marginTop: 2 }}>
              {c.work_title} — <span className="tabular-nums">₹{c.amount.toLocaleString('en-IN')}</span>
            </li>
          ))}
        </ul>
      )}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 'var(--space-2)', gap: 'var(--space-3)', fontSize: '0.625rem', color: 'var(--color-text-muted)' }}>
        <span>{evidence.note}</span>
        <span style={{ flexShrink: 0 }}>via {evidence.generation_source}</span>
      </div>
    </div>
  )
}

function useBudgetEvidence(workId: string) {
  const [open, setOpen] = useState(false)
  const [evidence, setEvidence] = useState<BudgetEvidenceResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const toggle = async () => {
    if (!open && !evidence) {
      setLoading(true)
      try {
        setEvidence(await api.budgetEvidence(workId))
      } catch { /* noop */ }
      setLoading(false)
    }
    setOpen(!open)
  }

  return { open, evidence, loading, toggle }
}

function FundedWorkRow({ workId, theme, villageName, cost }: {
  workId: string; theme: string; villageName: string | null; cost: number
}) {
  const { open, evidence, loading, toggle } = useBudgetEvidence(workId)

  return (
    <div className="list-row" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 'var(--space-2)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <span className={`badge badge-${theme}`}>{theme}</span>
          <span style={{ color: 'var(--color-text-secondary)' }}>{villageName || 'Unknown'}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <span className="tabular-nums" style={{ color: 'var(--color-text-tertiary)', fontSize: 'var(--text-xs)' }}>
            ₹{cost.toLocaleString('en-IN')}
          </span>
          <button onClick={toggle} className="btn btn-ghost btn-sm" style={{ gap: 4, fontSize: 'var(--text-xs)' }}>
            {loading ? <Spinner size={12} /> : <>{open ? <ChevronUp size={12} /> : <ChevronDown size={12} />} Why this much?</>}
          </button>
        </div>
      </div>
      <AnimatePresence>
        {open && evidence && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden' }}
          >
            <BudgetEvidencePanel evidence={evidence} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ExcludedCard({ workId, theme, villageName, score, budget }: {
  workId: string; theme: string; villageName: string | null; score: number; budget?: number
}) {
  const [open, setOpen] = useState(false)
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const evidenceState = useBudgetEvidence(workId)

  const handleToggle = async () => {
    if (!open && !explanation) {
      setLoading(true)
      try {
        const data = await api.explain(workId, budget)
        setExplanation(data)
      } catch { /* noop */ }
      setLoading(false)
    }
    setOpen(!open)
  }

  return (
    <div className="card" style={{ padding: 'var(--space-4)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
          <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
            {villageName || 'Unknown'}
          </span>
          <span className={`badge badge-${theme}`}>{theme}</span>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Score: {Math.round(score * 100)}%
          </span>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <button onClick={evidenceState.toggle} className="btn btn-ghost btn-sm" style={{ gap: 4, fontSize: 'var(--text-xs)' }}>
            {evidenceState.loading ? <Spinner size={14} /> : <>{evidenceState.open ? <ChevronUp size={14} /> : <ChevronDown size={14} />} Why this much?</>}
          </button>
          <button onClick={handleToggle} className="btn btn-ghost btn-sm" style={{ gap: 4, fontSize: 'var(--text-xs)' }}>
            {loading ? <Spinner size={14} /> : <>{open ? <ChevronUp size={14} /> : <ChevronDown size={14} />} Why not funded?</>}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {evidenceState.open && evidenceState.evidence && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden' }}
          >
            <BudgetEvidencePanel evidence={evidenceState.evidence} />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {open && explanation && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ marginTop: 'var(--space-4)', paddingTop: 'var(--space-3)', borderTop: '1px solid var(--color-border-default)' }}>
              {explanation.mp_explanation && (
                <div style={{ marginBottom: 'var(--space-3)' }}>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-tertiary)', marginBottom: 4 }}>For MP's office:</div>
                  <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
                    {explanation.mp_explanation}
                  </p>
                </div>
              )}
              {explanation.citizen_message && (
                <div style={{ marginBottom: 'var(--space-3)' }}>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-tertiary)', marginBottom: 4 }}>For citizens:</div>
                  <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
                    {explanation.citizen_message}
                  </p>
                </div>
              )}
              {explanation.generation_source && (
                <span style={{ fontSize: '0.625rem', color: 'var(--color-text-muted)' }}>
                  Generated via {explanation.generation_source}
                </span>
              )}
              {explanation.cutoff_caveat && (
                <div className="callout callout-warning" style={{ marginTop: 'var(--space-3)' }}>
                  <AlertTriangle size={14} /> <span>{explanation.cutoff_caveat}</span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function BudgetPage() {
  const { data: defaultAlloc, isLoading: dl, error: de, refetch } = useQuery({
    queryKey: ['allocation-default'],
    queryFn: () => api.allocation(),
  })

  const [budget, setBudget] = useState<number | null>(null)

  useEffect(() => {
    if (defaultAlloc && budget === null) setBudget(defaultAlloc.budget)
  }, [defaultAlloc, budget])

  const { data: alloc, isFetching: af } = useQuery({
    queryKey: ['allocation', budget],
    queryFn: () => api.allocation(budget!),
    enabled: budget !== null,
  })

  const { data: allWorks } = useQuery({
    queryKey: ['works', 500],
    queryFn: () => api.works(500),
  })

  if (dl) return <PageWrapper><LoadingState message="Loading budget data…" /></PageWrapper>
  if (de) return <PageWrapper><ErrorState message={(de as Error).message} onRetry={() => refetch()} /></PageWrapper>

  const current = alloc || defaultAlloc
  if (!current) return null

  const selectedIds = new Set(current.selected_works.map((w) => w.work_id))
  const excluded = allWorks?.filter((w) => !selectedIds.has(w.work_id)).slice(0, 15) || []

  return (
    <PageWrapper>
      <PageHeader
        title="Budget Simulator"
        subtitle="Explore how budget allocation affects which development works get funded"
      />

      {/* Slider */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 'var(--space-3)' }}>
          <label htmlFor="budget-slider" style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
            Budget
          </label>
          <span style={{ fontSize: 'var(--text-xl)', fontWeight: 650, color: 'var(--color-text-primary)', fontVariantNumeric: 'tabular-nums' }}>
            ₹{(budget ?? 0).toLocaleString('en-IN')}
          </span>
        </div>
        <input
          id="budget-slider"
          type="range"
          min={500_000}
          max={25_000_000}
          step={500_000}
          value={budget ?? 5_000_000}
          onChange={(e) => setBudget(Number(e.target.value))}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-1)' }}>
          <span>₹5L</span>
          <span>₹2.5Cr</span>
        </div>
        {current.is_default_budget && (
          <p style={{ marginTop: 'var(--space-3)', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Default: Bagalkot's current (18th Lok Sabha) MPLADS allocated limit.
          </p>
        )}
      </div>

      {/* Stats */}
      <div style={{ position: 'relative', marginTop: 'var(--space-5)' }}>
        {af && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(10, 10, 11, 0.6)', borderRadius: 'var(--radius-lg)', zIndex: 10,
          }}>
            <Spinner size={26} />
          </div>
        )}
        <MetricGrid>
          <Metric
            label="Works funded"
            value={current.n_works_selected.toString()}
            sub={`of ${current.n_candidates_considered} candidates`}
          />
          <Metric
            label="Budget used"
            value={`${Math.round(current.budget_used_pct * 100)}%`}
            sub={`₹${current.total_cost.toLocaleString('en-IN')}`}
          />
          <Metric
            label="Total priority value"
            value={current.total_value.toFixed(1)}
            sub="composite score sum"
          />
        </MetricGrid>
      </div>

      <p style={{ marginTop: 'var(--space-3)', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
        {current.cost_heuristic_note}
      </p>

      {/* Selected works */}
      <div className="card card-flush" style={{ marginTop: 'var(--space-5)' }}>
        <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 'var(--space-5) var(--space-5) var(--space-3)' }}>
          <CheckCircle2 size={16} style={{ color: 'var(--status-good)' }} />
          Funded works
        </h3>
        <div style={{ padding: '0 var(--space-3) var(--space-3)' }}>
          {current.selected_works.slice(0, 15).map((w) => (
            <FundedWorkRow key={w.work_id} workId={w.work_id} theme={w.theme} villageName={w.village_name} cost={w.cost} />
          ))}
          {current.selected_works.length > 15 && (
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', textAlign: 'center', padding: 'var(--space-2) 0' }}>
              …and {current.selected_works.length - 15} more
            </p>
          )}
        </div>
      </div>

      {/* Excluded works */}
      {excluded.length > 0 && (
        <div style={{ marginTop: 'var(--space-6)' }}>
          <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 'var(--space-4)' }}>
            <XCircle size={16} style={{ color: 'var(--color-text-muted)' }} />
            Not funded this cycle
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {excluded.map((w) => (
              <ExcludedCard
                key={w.work_id}
                workId={w.work_id}
                theme={w.theme}
                villageName={w.village_name}
                score={w.composite_score}
                budget={budget ?? undefined}
              />
            ))}
          </div>
        </div>
      )}
    </PageWrapper>
  )
}
