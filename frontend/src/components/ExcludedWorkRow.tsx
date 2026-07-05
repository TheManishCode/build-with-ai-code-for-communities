import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Work } from '../api/types'

const SOURCE_LABEL: Record<string, string> = {
  nvidia: 'NVIDIA (base model)',
  claude: 'Claude (backup model)',
  template: 'Template (no model output passed verification)',
}

export function ExcludedWorkRow({ work, budget }: { work: Work; budget: number | null }) {
  const [expanded, setExpanded] = useState(false)
  const { data, isFetching } = useQuery({
    queryKey: ['explain', work.work_id, budget],
    queryFn: () => api.explain(work.work_id, budget ?? undefined),
    enabled: expanded,
  })

  return (
    <div className="rounded-md border border-gray-200 bg-white p-3 text-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center justify-between">
        <div>
          <span className="font-medium text-gray-900 dark:text-gray-100">{work.village_name ?? 'Unresolved'}</span>
          <span className="ml-2 text-gray-500">({work.theme})</span>
          <span className="ml-2 text-xs text-gray-400">score {Math.round(work.composite_score * 100)}</span>
        </div>
        <button
          onClick={() => setExpanded((v) => !v)}
          className="rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
        >
          {expanded ? 'Hide' : 'Why not funded?'}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 border-t border-gray-100 pt-3 dark:border-gray-700">
          {isFetching && <p className="text-xs text-gray-400">Generating explanation...</p>}
          {data && !data.is_funded && (
            <div className="flex flex-col gap-3">
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">MP office explanation</p>
                <p className="text-gray-700 dark:text-gray-300">{data.mp_explanation}</p>
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">Citizen-facing message</p>
                <p className="text-gray-700 dark:text-gray-300">{data.citizen_message}</p>
              </div>
              {data.cutoff_caveat && <p className="text-xs italic text-gray-400">{data.cutoff_caveat}</p>}
              <p className="text-xs text-gray-400">
                Source: {SOURCE_LABEL[data.generation_source ?? 'template']}
                {data.fallback_reason ? ` (${data.fallback_reason})` : ''}
              </p>
            </div>
          )}
          {data && data.is_funded && <p className="text-xs text-gray-400">This work is actually funded at the current budget.</p>}
        </div>
      )}
    </div>
  )
}
