import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Work } from '../api/types'
import { Card } from './ui/Card'
import { Button } from './ui/Button'
import { ThemeBadge } from './ui/Badge'

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
    <Card className="p-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-neutral-900 dark:text-neutral-100">{work.village_name ?? 'Unresolved'}</span>
          <ThemeBadge theme={work.theme} />
          <span className="text-xs text-neutral-400">score {Math.round(work.composite_score * 100)}</span>
        </div>
        <Button variant="secondary" className="shrink-0 px-2.5 py-1 text-xs" onClick={() => setExpanded((v) => !v)}>
          {expanded ? 'Hide' : 'Why not funded?'}
        </Button>
      </div>

      {expanded && (
        <div className="mt-3 border-t border-neutral-100 pt-3 dark:border-neutral-800">
          {isFetching && <p className="text-xs text-neutral-400">Generating explanation...</p>}
          {data && !data.is_funded && (
            <div className="flex flex-col gap-3">
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">MP office explanation</p>
                <p className="text-neutral-700 dark:text-neutral-300">{data.mp_explanation}</p>
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">Citizen-facing message</p>
                <p className="text-neutral-700 dark:text-neutral-300">{data.citizen_message}</p>
              </div>
              {data.cutoff_caveat && <p className="text-xs italic text-neutral-400">{data.cutoff_caveat}</p>}
              <p className="text-xs text-neutral-400">
                Source: {SOURCE_LABEL[data.generation_source ?? 'template']}
                {data.fallback_reason ? ` (${data.fallback_reason})` : ''}
              </p>
            </div>
          )}
          {data && data.is_funded && <p className="text-xs text-neutral-400">This work is actually funded at the current budget.</p>}
        </div>
      )}
    </Card>
  )
}
