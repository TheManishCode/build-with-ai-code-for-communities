import { useState } from 'react'
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
  const [showQuotes, setShowQuotes] = useState(false)
  const hasQuotes = work.source_quotes.length > 0

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
        <div className="flex gap-2">
          {hasQuotes && (
            <button
              onClick={() => setShowQuotes((v) => !v)}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              {showQuotes ? 'Hide' : 'In their words'} ({work.source_quotes.length})
            </button>
          )}
          <button
            onClick={() => onDraftLetter(work.work_id)}
            className="rounded-md bg-gray-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-gray-700 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
          >
            Generate draft letter
          </button>
        </div>
      </div>

      {showQuotes && hasQuotes && (
        <div className="mt-3 flex flex-col gap-2 border-t border-gray-100 pt-3 dark:border-gray-700">
          {work.source_quotes.map((q) => (
            <div key={q.submission_id} className="rounded-md bg-gray-50 p-2.5 text-xs dark:bg-gray-900">
              <p className="italic text-gray-700 dark:text-gray-300">
                "{q.original_text}"
                <span className="ml-1 not-italic text-gray-400">({q.original_language})</span>
              </p>
              {q.original_language !== 'en' && q.translated_text && (
                <p className="mt-1 text-gray-500">Translated: "{q.translated_text}"</p>
              )}
              <p className="mt-1 text-gray-400">
                Submission #{q.submission_id}
                {q.village ? ` · ${q.village}` : ''}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
