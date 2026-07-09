import type { ReactNode } from 'react'

/** A ledger summary column -- a bottom hairline instead of a boxed card, so a row of these
 * reads as one register strip rather than a grid of separate dashboard widgets. */
export function StatTile({
  label,
  value,
  sub,
  icon,
}: {
  label: string
  value: string
  sub?: string
  icon?: ReactNode
}) {
  return (
    <div className="border-b border-stone-200 pb-3 dark:border-stone-800">
      <div className="flex items-center gap-1.5 text-stone-400 dark:text-stone-500">
        {icon}
        <span className="text-[11px] font-semibold uppercase tracking-wide">{label}</span>
      </div>
      <div className="mt-1.5 font-display text-[1.75rem] font-medium leading-none tabular-nums text-stone-900 dark:text-stone-50">
        {value}
      </div>
      {sub && <div className="mt-1.5 text-xs text-stone-500 dark:text-stone-400">{sub}</div>}
    </div>
  )
}
