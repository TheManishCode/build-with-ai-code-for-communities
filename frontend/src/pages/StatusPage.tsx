import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, CheckCircle2, AlertCircle, Hash } from 'lucide-react'
import { api } from '../api/client'
import { PageWrapper, PageHeader } from '../components/ui/PageWrapper'
import { Spinner } from '../components/ui/StateDisplays'

function DetailField({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div>
      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginBottom: 3 }}>{label}</div>
      <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
        {value ?? '—'}
      </div>
    </div>
  )
}

export function StatusPage() {
  const [inputVal, setInputVal] = useState('')
  const [submissionId, setSubmissionId] = useState<number | null>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['citizenStatus', submissionId],
    queryFn: () => api.citizenStatus(submissionId!),
    enabled: submissionId !== null,
    retry: false,
  })

  const handleSubmit = () => {
    const parsed = parseInt(inputVal, 10)
    if (!isNaN(parsed) && parsed > 0) setSubmissionId(parsed)
  }

  const tierBadge = () => {
    if (!data) return null
    if (data.is_funded_this_cycle) {
      return (
        <span style={{
          padding: '3px 10px', borderRadius: 'var(--radius-full)',
          fontSize: 'var(--text-xs)', fontWeight: 650,
          background: 'rgba(47, 179, 68, 0.14)', color: 'var(--status-good)',
          display: 'flex', alignItems: 'center', gap: 5,
        }}>
          <CheckCircle2 size={12} />
          Funded
        </span>
      )
    }
    if (data.funding_tier.startsWith('High Priority')) {
      return (
        <span style={{
          padding: '3px 10px', borderRadius: 'var(--radius-full)',
          fontSize: 'var(--text-xs)', fontWeight: 650,
          background: 'var(--color-accent-dim)', color: 'var(--color-accent)',
        }}>
          High Priority
        </span>
      )
    }
    return (
      <span style={{
        padding: '3px 10px', borderRadius: 'var(--radius-full)',
        fontSize: 'var(--text-xs)', fontWeight: 650,
        background: 'var(--color-bg-elevated)', color: 'var(--color-text-tertiary)',
      }}>
        {data.funding_tier}
      </span>
    )
  }

  return (
    <PageWrapper>
      <PageHeader
        title="Check Your Report"
        subtitle="Enter your submission ID to see what happened to your report"
      />

      {/* Search input */}
      <div style={{ maxWidth: 460, margin: '0 auto var(--space-8)' }}>
        <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Hash size={15} style={{
              position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
              color: 'var(--color-text-muted)',
            }} />
            <input
              className="input"
              type="text"
              placeholder="e.g. 54"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              style={{ paddingLeft: 34 }}
              aria-label="Submission ID"
            />
          </div>
          <button onClick={handleSubmit} className="btn btn-primary" disabled={!inputVal.trim()}>
            <Search size={15} /> Check
          </button>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-10)' }}>
          <Spinner size={26} />
        </div>
      )}

      {/* Error */}
      {error && submissionId !== null && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="error-banner"
          style={{ maxWidth: 460, margin: '0 auto' }}
        >
          <AlertCircle size={16} />
          <span>Submission #{submissionId} not found. Check the ID and try again.</span>
        </motion.div>
      )}

      {/* Result */}
      <AnimatePresence>
        {data && (
          <motion.div
            className="card"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.25 }}
            style={{ maxWidth: 560, margin: '0 auto' }}
          >
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
              <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 650, color: 'var(--color-text-primary)' }}>
                Submission #{data.submission_id}
              </h3>
              {tierBadge()}
            </div>

            {/* Status message */}
            <p style={{
              fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)',
              lineHeight: 'var(--leading-relaxed)',
              padding: 'var(--space-3) var(--space-4)',
              background: 'var(--color-bg-elevated)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-5)',
            }}>
              {data.status_message}
            </p>

            {/* Details grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 'var(--space-4)',
            }}>
              <DetailField label="Village" value={data.village} />
              <DetailField label="Taluk" value={data.taluk} />
              <DetailField label="Theme" value={data.theme} />
              <DetailField label="Dedup group" value={data.dedup_group_id} />
              <DetailField label="Corroboration" value={data.corroboration_count != null ? `${data.corroboration_count} reports` : null} />
              <DetailField
                label="Current rank"
                value={data.current_rank != null && data.total_works_ranked != null
                  ? `#${data.current_rank} of ${data.total_works_ranked}`
                  : null
                }
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </PageWrapper>
  )
}
