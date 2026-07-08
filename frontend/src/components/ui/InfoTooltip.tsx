import { Info } from 'lucide-react'
import { useId } from 'react'

/** A small (i) affordance that reveals a one- or two-sentence methodology note on hover or
 * keyboard focus -- used throughout the app so every number that isn't self-explanatory has
 * its "why" one interaction away, without cluttering the primary layout. */
export function InfoTooltip({ label, children }: { label: string; children: React.ReactNode }) {
  const id = useId()
  return (
    <span className="group relative inline-flex items-center">
      <button
        type="button"
        aria-describedby={id}
        className="inline-flex rounded-full text-neutral-400 hover:text-neutral-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 dark:text-neutral-500 dark:hover:text-neutral-300"
      >
        <span className="sr-only">{label}</span>
        <Info size={14} aria-hidden="true" />
      </button>
      <span
        role="tooltip"
        id={id}
        className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 w-56 -translate-x-1/2 rounded-md bg-neutral-900 px-3 py-2 text-xs leading-relaxed text-neutral-50 opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 dark:bg-neutral-100 dark:text-neutral-900"
      >
        {children}
      </span>
    </span>
  )
}
