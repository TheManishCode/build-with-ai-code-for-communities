import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Clock, Search } from 'lucide-react'
import { api } from '../api/client'
import { Card } from './ui/Card'
import { Button } from './ui/Button'
import { StatusBadge } from './ui/Badge'
import { PageHeader } from './ui/PageState'

export function CitizenStatusLookup({ initialSubmissionId }: { initialSubmissionId?: number } = {}) {
  const [inputValue, setInputValue] = useState(initialSubmissionId != null ? String(initialSubmissionId) : '')
  const [submittedId, setSubmittedId] = useState<number | null>(initialSubmissionId ?? null)

  const { data, isFetching, error } = useQuery({
    queryKey: ['citizen-status', submittedId],
    queryFn: () => api.citizenStatus(submittedId!),
    enabled: submittedId !== null,
    retry: false,
  })

  const handleLookup = () => {
    const id = Number(inputValue)
    if (Number.isFinite(id) && id > 0) setSubmittedId(id)
  }

  const tone = data?.is_funded_this_cycle ? 'good' : data?.funding_tier.startsWith('High Priority') ? 'warning' : 'neutral'

  return (
    <div className="mx-auto max-w-lg p-4">
      <PageHeader title="Check Your Report Status" subtitle="Enter your submission ID to see what happened to your report." />

      <label htmlFor="submission-id-input" className="sr-only">
        Submission ID
      </label>
      <div className="flex gap-2">
        <input
          id="submission-id-input"
          type="number"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleLookup()}
          placeholder="Submission ID, e.g. 54"
          className="flex-1 rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100"
        />
        <Button onClick={handleLookup} className="flex items-center gap-1.5">
          <Search size={14} aria-hidden="true" />
          Check Status
        </Button>
      </div>

      {isFetching && <p className="mt-4 text-sm text-neutral-400">Looking up your report...</p>}

      {error && (
        <div className="mt-4 rounded-lg border border-critical/20 bg-critical/5 p-3 text-sm text-critical dark:bg-critical/10">
          No submission found with that ID. Double-check the number and try again.
        </div>
      )}

      {data && (
        <Card className="mt-4 p-5">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Submission #{data.submission_id}</span>
            <StatusBadge tone={tone}>
              {tone === 'good' ? <CheckCircle2 size={12} aria-hidden="true" /> : <Clock size={12} aria-hidden="true" />}
              {data.funding_tier}
            </StatusBadge>
          </div>

          <p className="text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">{data.status_message}</p>

          <div className="mt-4 grid grid-cols-2 gap-3 border-t border-neutral-100 pt-4 text-sm dark:border-neutral-800">
            <Field label="Village" value={data.village ?? '—'} />
            <Field label="Taluk" value={data.taluk ?? '—'} />
            <Field label="Theme" value={data.theme ?? '—'} />
            <Field label="Dedup group" value={data.dedup_group_id != null ? `#${data.dedup_group_id}` : '—'} />
            <Field label="Merged reports" value={data.corroboration_count != null ? String(data.corroboration_count) : '—'} />
            <Field
              label="Current rank"
              value={data.current_rank != null ? `#${data.current_rank} of ${data.total_works_ranked}` : '—'}
            />
          </div>
        </Card>
      )}
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-neutral-400">{label}</div>
      <div className="font-medium text-neutral-900 dark:text-neutral-100">{value}</div>
    </div>
  )
}
