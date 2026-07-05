import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { WorkCard } from './WorkCard'
import { DraftLetterModal } from './DraftLetterModal'

export function WorksList() {
  const [limit, setLimit] = useState(20)
  const [letterWorkId, setLetterWorkId] = useState<string | null>(null)
  const { data: works, isLoading, error } = useQuery({ queryKey: ['works', limit], queryFn: () => api.works(limit) })

  if (isLoading) return <div className="p-6 text-gray-500">Loading ranked works...</div>
  if (error) return <div className="p-6 text-red-600">Failed to load works: {(error as Error).message}</div>

  return (
    <div className="mx-auto max-w-3xl p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Ranked Priority List</h2>
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="rounded-md border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800"
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
