import { useState } from 'react'
import { FileText, MessageSquareQuote, Users } from 'lucide-react'
import type { Work } from '../api/types'
import { Card } from './ui/Card'
import { Button } from './ui/Button'
import { ThemeBadge } from './ui/Badge'
import { Meter } from './ui/Meter'
import { InfoTooltip } from './ui/InfoTooltip'

export function WorkCard({
  work,
  rank,
  onDraftLetter,
}: {
  work: Work
  rank?: number
  onDraftLetter: (workId: string) => void
}) {
  const scorePct = Math.round(work.composite_score * 100)
  const [showQuotes, setShowQuotes] = useState(false)
  const hasQuotes = work.source_quotes.length > 0

  return (
    <Card className="p-4 sm:p-5">
      <div className="flex gap-4">
        {rank != null && (
          <div
            className="hidden w-7 shrink-0 pt-0.5 text-right font-display text-base font-medium tabular-nums text-gold-600 dark:text-gold-400 sm:block"
            aria-hidden="true"
          >
            {String(rank).padStart(2, '0')}
          </div>
        )}

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <ThemeBadge theme={work.theme} />
              {work.source === 'gap' && (
                <span className="inline-flex items-center rounded-full bg-gold-100 px-2.5 py-0.5 text-xs font-medium text-gold-800 dark:bg-gold-900/40 dark:text-gold-200">
                  silent need
                </span>
              )}
              <span className="text-sm font-semibold text-stone-900 dark:text-stone-50">
                {work.village_name ?? 'Unresolved location'}
              </span>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-1">
              <div className="flex items-center gap-1">
                <span className="font-display text-xl font-medium tabular-nums text-stone-900 dark:text-stone-50">{scorePct}</span>
                <InfoTooltip label="How the priority score works">
                  Composite of two constituency-wide percentiles: <strong>demand</strong> (citizen
                  reports, recency-weighted) and <strong>gap</strong> (objective infrastructure
                  shortfall vs. Census/amenities data).
                </InfoTooltip>
              </div>
              <Meter value={work.composite_score} className="w-20" />
            </div>
          </div>

          <p className="mt-3 text-sm leading-relaxed text-stone-700 dark:text-stone-300">{work.reasoning}</p>

          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-stone-500 dark:text-stone-400">
            <div className="flex gap-4">
              <span className="flex items-center gap-1">
                <Users size={13} aria-hidden="true" />
                {work.corroboration_count} report{work.corroboration_count === 1 ? '' : 's'}
              </span>
              {work.population_affected != null && <span>{work.population_affected.toLocaleString()} people affected</span>}
            </div>
            <div className="flex gap-2">
              {hasQuotes && (
                <Button variant="secondary" className="flex items-center gap-1.5 px-3 py-1.5 text-xs" onClick={() => setShowQuotes((v) => !v)}>
                  <MessageSquareQuote size={13} aria-hidden="true" />
                  {showQuotes ? 'Hide' : 'In their words'} ({work.source_quotes.length})
                </Button>
              )}
              <Button className="flex items-center gap-1.5 px-3 py-1.5 text-xs" onClick={() => onDraftLetter(work.work_id)}>
                <FileText size={13} aria-hidden="true" />
                Generate draft letter
              </Button>
            </div>
          </div>

          {showQuotes && hasQuotes && (
            <div className="mt-3 flex flex-col gap-2 border-t border-stone-200 pt-3 dark:border-stone-800">
              {work.source_quotes.map((q) => (
                <div key={q.submission_id} className="rounded-md bg-stone-100 p-2.5 text-xs dark:bg-stone-800">
                  <p className="italic text-stone-700 dark:text-stone-300" lang={q.original_language}>
                    &ldquo;{q.original_text}&rdquo;
                    <span className="ml-1 not-italic text-stone-500 dark:text-stone-400" lang="en">
                      ({q.original_language})
                    </span>
                  </p>
                  {q.original_language !== 'en' && q.translated_text && (
                    <p className="mt-1 text-stone-600 dark:text-stone-400" lang="en">
                      Translated: &ldquo;{q.translated_text}&rdquo;
                    </p>
                  )}
                  <p className="mt-1 text-stone-500 dark:text-stone-400">
                    Submission #{q.submission_id}
                    {q.village ? ` · ${q.village}` : ''}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}
