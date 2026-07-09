import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, Clock, Search } from 'lucide-react'
import { motion } from 'motion/react'
import { api } from '../api/client'
import { Card } from './ui/Card'
import { Button } from './ui/Button'
import { StatusBadge } from './ui/Badge'
import { PageHeader } from './ui/PageState'
import { springy } from '../lib/motion'

export function CitizenStatusLookup() {
  const { submissionId: paramId } = useParams<{ submissionId?: string }>()
  const navigate = useNavigate()
  const [inputValue, setInputValue] = useState(paramId ?? '')

  useEffect(() => {
    if (paramId) setInputValue(paramId)
  }, [paramId])

  const submittedId = paramId != null && paramId !== '' ? Number(paramId) : null
  const validId = submittedId != null && Number.isFinite(submittedId) && submittedId > 0

  const { data, isFetching, error } = useQuery({
    queryKey: ['citizen-status', submittedId],
    queryFn: () => api.citizenStatus(submittedId!),
    enabled: validId,
    retry: false,
  })

  const handleLookup = () => {
    const id = Number(inputValue)
    if (Number.isFinite(id) && id > 0) navigate(`/status/${id}`)
  }

  const tone = data?.is_funded_this_cycle ? 'good' : data?.funding_tier.startsWith('High Priority') ? 'warning' : 'neutral'

  return (
    <div className="mx-auto max-w-lg px-4">
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
          className="flex-1 rounded-md border border-stone-300 bg-stone-50 px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100"
        />
        <Button onClick={handleLookup} className="flex items-center gap-1.5">
          <Search size={14} aria-hidden="true" />
          Check Status
        </Button>
      </div>

      {isFetching && <p className="mt-4 text-sm text-stone-400">Looking up your report...</p>}

      {error && (
        <div className="mt-4 rounded-md border border-critical/20 bg-critical/5 p-3 text-sm text-critical dark:bg-critical/10">
          No submission found with that ID. Double-check the number and try again.
        </div>
      )}

      {data && (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={springy}>
          <Card className="mt-4 p-5">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-sm font-medium text-stone-500 dark:text-stone-400">Submission #{data.submission_id}</span>
              <StatusBadge tone={tone}>
                {tone === 'good' ? <CheckCircle2 size={12} aria-hidden="true" /> : <Clock size={12} aria-hidden="true" />}
                {data.funding_tier}
              </StatusBadge>
            </div>

            <p className="text-sm leading-relaxed text-stone-700 dark:text-stone-300">{data.status_message}</p>

            <div className="mt-4 grid grid-cols-2 gap-3 border-t border-stone-200 pt-4 text-sm dark:border-stone-800">
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
        </motion.div>
      )}
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-stone-400">{label}</div>
      <div className="font-medium tabular-nums text-stone-900 dark:text-stone-100">{value}</div>
    </div>
  )
}
