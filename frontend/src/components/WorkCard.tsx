import type { Work } from '../api/types'

const THEME_COLORS: Record<string, string> = {
  water: 'bg-blue-100 text-blue-800',
  road: 'bg-amber-100 text-amber-800',
  school: 'bg-violet-100 text-violet-800',
  health: 'bg-rose-100 text-rose-800',
  electricity: 'bg-yellow-100 text-yellow-800',
  sanitation: 'bg-emerald-100 text-emerald-800',
  other: 'bg-gray-100 text-gray-800',
}

export function WorkCard({ work, onDraftLetter }: { work: Work; onDraftLetter: (workId: string) => void }) {
  const themeClass = THEME_COLORS[work.theme] ?? THEME_COLORS.other
  const scorePct = Math.round(work.composite_score * 100)

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${themeClass}`}>{work.theme}</span>
          {work.source === 'gap' && (
            <span className="rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800">
              silent need
            </span>
          )}
          <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {work.village_name ?? 'Unresolved location'}
          </span>
        </div>
        <div className="flex flex-col items-end shrink-0">
          <span className="text-lg font-bold tabular-nums text-gray-900 dark:text-gray-100">{scorePct}</span>
          <span className="text-xs text-gray-500">priority score</span>
        </div>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-gray-700 dark:text-gray-300">{work.reasoning}</p>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-500">
        <div className="flex gap-4">
          <span>{work.corroboration_count} report{work.corroboration_count === 1 ? '' : 's'}</span>
          {work.population_affected != null && <span>{work.population_affected.toLocaleString()} people affected</span>}
        </div>
        <button
          onClick={() => onDraftLetter(work.work_id)}
          className="rounded-md bg-gray-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-gray-700 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
        >
          Generate draft letter
        </button>
      </div>
    </div>
  )
}
