import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { motion } from 'motion/react'
import { api } from '../api/client'
import { WorkCard } from './WorkCard'
import { DraftLetterModal } from './DraftLetterModal'
import { Loading, ErrorState, PageHeader } from './ui/PageState'
import { listParent, listItem } from '../lib/motion'

export function WorksList() {
  const [limit, setLimit] = useState(20)
  const [letterWorkId, setLetterWorkId] = useState<string | null>(null)
  const { data: works, isLoading, error } = useQuery({ queryKey: ['works', limit], queryFn: () => api.works(limit) })

  if (isLoading) return <Loading label="Loading ranked works..." />
  if (error) return <ErrorState label={`Failed to load works: ${(error as Error).message}`} />

  return (
    <div className="mx-auto max-w-3xl px-4">
      <div className="mb-5 flex items-end justify-between gap-3">
        <PageHeader
          title="Ranked Priority List"
          subtitle="Every citizen report and infrastructure gap, ranked by one composite score."
        />
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="mb-6 shrink-0 rounded-md border border-stone-300 bg-stone-50 px-2.5 py-1.5 text-sm text-stone-700 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-200"
        >
          <option value={10}>Top 10</option>
          <option value={20}>Top 20</option>
          <option value={50}>Top 50</option>
        </select>
      </div>

      <motion.div initial="hidden" animate="visible" variants={listParent} className="flex flex-col gap-3">
        {works?.map((w, i) => (
          <motion.div key={w.work_id} variants={listItem}>
            <WorkCard work={w} rank={i + 1} onDraftLetter={setLetterWorkId} />
          </motion.div>
        ))}
      </motion.div>

      {letterWorkId && <DraftLetterModal workId={letterWorkId} onClose={() => setLetterWorkId(null)} />}
    </div>
  )
}
