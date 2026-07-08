import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { WorkCard } from './WorkCard'
import { DraftLetterModal } from './DraftLetterModal'
import { Loading, ErrorState } from './ui/PageState'

export function WorksList() {
  const [limit, setLimit] = useState(20)
  const [letterWorkId, setLetterWorkId] = useState<string | null>(null)
  const { data: works, isLoading, error } = useQuery({ queryKey: ['works', limit], queryFn: () => api.works(limit) })

  if (isLoading) return <Loading label="Loading ranked works..." />
  if (error) return <ErrorState label={`Failed to load works: ${(error as Error).message}`} />

  return (
    <div className="mx-auto max-w-3xl p-4">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">Ranked Priority List</h2>
          <p className="mt-0.5 text-sm text-neutral-500 dark:text-neutral-400">
            Every citizen report and infrastructure gap, ranked by one composite score.
          </p>
        </div>
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="rounded-lg border border-neutral-300 bg-white px-2.5 py-1.5 text-sm text-neutral-700 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-200"
        >
          <option value={10}>Top 10</option>
          <option value={20}>Top 20</option>
          <option value={50}>Top 50</option>
        </select>
      </div>

      <div className="flex flex-col gap-3">
        {works?.map((w) => (
          <WorkCard key={w.work_id} work={w} onDraftLetter={setLetterWorkId} />
        ))}
      </div>

      {letterWorkId && <DraftLetterModal workId={letterWorkId} onClose={() => setLetterWorkId(null)} />}
    </div>
  )
}
