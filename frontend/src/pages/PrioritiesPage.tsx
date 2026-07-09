import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, Quote, FileEdit, AlertTriangle } from 'lucide-react'
import { api } from '../api/client'
import type { Work } from '../api/types'
import { PageWrapper, PageHeader } from '../components/ui/PageWrapper'
import { LoadingState, ErrorState, EmptyState } from '../components/ui/StateDisplays'
import { DraftLetterModal } from '../components/DraftLetterModal'

const THEME_LABELS: Record<string, string> = {
  water: 'Water', road: 'Roads', school: 'Education',
  health: 'Health', electricity: 'Electricity', sanitation: 'Sanitation',
}

function WorkCard({ work, index, onDraft }: { work: Work; index: number; onDraft: (id: string) => void }) {
  const [quotesOpen, setQuotesOpen] = useState(false)
  const themeClass = `badge badge-${work.theme}`
  const scorePercent = Math.round(work.composite_score * 100)

  return (
    <motion.div
      className="card"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: Math.min(index, 8) * 0.03 }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
          <span style={{ fontSize: 'var(--text-xs)', fontWeight: 650, color: 'var(--color-text-muted)', fontVariantNumeric: 'tabular-nums' }}>
            #{index + 1}
          </span>
          <span className={themeClass}>{THEME_LABELS[work.theme] || work.theme}</span>
          {work.source === 'gap' && <span className="badge badge-silent">Silent need</span>}
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 650, color: 'var(--color-text-primary)', lineHeight: 1, letterSpacing: '-0.02em' }}>
            {scorePercent}%
          </div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--color-text-muted)', marginTop: 2 }}>priority score</div>
        </div>
      </div>

      {/* Village & reasoning */}
      <div style={{ marginTop: 'var(--space-4)' }}>
        <div style={{ fontSize: 'var(--text-sm)', fontWeight: 650, color: 'var(--color-text-primary)' }}>
          {work.village_name || 'Unknown Village'}
        </div>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 'var(--leading-relaxed)', marginTop: 'var(--space-2)' }}>
          {work.reasoning}
        </p>
      </div>

      {/* Stats row */}
      <div style={{ display: 'flex', gap: 'var(--space-5)', marginTop: 'var(--space-4)', fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)' }}>
        <span><strong style={{ color: 'var(--color-text-secondary)' }}>{work.corroboration_count}</strong> reports</span>
        {work.population_affected != null && (
          <span><strong style={{ color: 'var(--color-text-secondary)' }}>{work.population_affected.toLocaleString('en-IN')}</strong> people affected</span>
        )}
        {work.gap_percentile != null && (
          <span>Gap: <strong style={{ color: 'var(--color-text-secondary)' }}>{Math.round(work.gap_percentile * 100)}%</strong>ile</span>
        )}
      </div>

      {/* Source quotes section */}
      {work.source_quotes && work.source_quotes.length > 0 && (
        <div style={{ marginTop: 'var(--space-4)', borderTop: '1px solid var(--color-border-default)', paddingTop: 'var(--space-3)' }}>
          <button
            onClick={() => setQuotesOpen(!quotesOpen)}
            className="btn btn-ghost btn-sm"
            style={{ gap: 6, fontSize: 'var(--text-xs)' }}
          >
            <Quote size={13} />
            In their words ({work.source_quotes.length})
            {quotesOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
          <AnimatePresence>
            {quotesOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                style={{ overflow: 'hidden' }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', marginTop: 'var(--space-3)' }}>
                  {work.source_quotes.map((q, qi) => (
                    <div key={qi} style={{
                      padding: 'var(--space-3)',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--color-bg-elevated)',
                      borderLeft: '2px solid var(--color-border-strong)',
                    }}>
                      <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', fontStyle: 'italic' }}>
                        "{q.original_text}"
                      </p>
                      {q.translated_text && q.original_language !== 'en' && (
                        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-tertiary)', marginTop: 'var(--space-1)' }}>
                          → {q.translated_text}
                        </p>
                      )}
                      <div style={{ fontSize: '0.625rem', color: 'var(--color-text-muted)', marginTop: 'var(--space-1)' }}>
                        Submission #{q.submission_id} · {q.original_language}
                        {q.village && ` · ${q.village}`}
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', marginTop: 'var(--space-4)' }}>
        <button onClick={() => onDraft(work.work_id)} className="btn btn-primary btn-sm">
          <FileEdit size={14} /> Draft letter
        </button>
      </div>
    </motion.div>
  )
}

export function PrioritiesPage() {
  const [limit, setLimit] = useState(20)
  const [letterWorkId, setLetterWorkId] = useState<string | null>(null)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['works', limit],
    queryFn: () => api.works(limit),
  })

  if (isLoading) return <PageWrapper><LoadingState message="Loading ranked priorities…" /></PageWrapper>
  if (error) return <PageWrapper><ErrorState message={(error as Error).message} onRetry={() => refetch()} /></PageWrapper>

  return (
    <PageWrapper>
      <PageHeader
        title="Ranked Priorities"
        subtitle="Development works ranked by citizen demand and infrastructure gap analysis"
        actions={
          <select
            className="input select"
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            style={{ width: 'auto', minWidth: 100 }}
            aria-label="Number of works to display"
          >
            <option value={10}>Top 10</option>
            <option value={20}>Top 20</option>
            <option value={50}>Top 50</option>
          </select>
        }
      />

      {!data || data.length === 0 ? (
        <EmptyState
          icon={<AlertTriangle size={40} />}
          title="No works found"
          description="No candidate works are available at this time."
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {data.map((work, i) => (
            <WorkCard key={work.work_id} work={work} index={i} onDraft={setLetterWorkId} />
          ))}
        </div>
      )}

      <AnimatePresence>
        {letterWorkId && (
          <DraftLetterModal workId={letterWorkId} onClose={() => setLetterWorkId(null)} />
        )}
      </AnimatePresence>
    </PageWrapper>
  )
}
