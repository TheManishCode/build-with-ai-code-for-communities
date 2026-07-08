import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

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

  return (
    <div className="mx-auto max-w-lg p-4">
      <h2 className="mb-1 text-lg font-semibold text-gray-900 dark:text-gray-100">Check Your Report Status</h2>
      <p className="mb-4 text-sm text-gray-500">Enter your submission ID to see what happened to your report.</p>

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
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        />
        <button
          onClick={handleLookup}
          className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 dark:bg-gray-100 dark:text-gray-900"
        >
          Check Status
        </button>
      </div>

      {isFetching && <p className="mt-4 text-sm text-gray-400">Looking up your report...</p>}

      {error && (
        <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          No submission found with that ID. Double-check the number and try again.
        </div>
      )}

      {data && (
        <div className="mt-4 rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-500">Submission #{data.submission_id}</span>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                data.is_funded_this_cycle
                  ? 'bg-green-100 text-green-800'
                  : data.funding_tier.startsWith('High Priority')
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-gray-100 text-gray-800'
              }`}
            >
              {data.funding_tier}
            </span>
          </div>

          <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">{data.status_message}</p>

          <div className="mt-4 grid grid-cols-2 gap-3 border-t border-gray-100 pt-4 text-sm dark:border-gray-700">
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
        </div>
      )}
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-gray-400">{label}</div>
      <div className="font-medium text-gray-900 dark:text-gray-100">{value}</div>
    </div>
  )
}
