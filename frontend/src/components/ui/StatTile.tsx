import type { ReactNode } from 'react'
import { Card } from './Card'

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
    <Card className="p-4">
      <div className="flex items-center gap-2 text-neutral-400 dark:text-neutral-500">
        {icon}
        <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">{label}</span>
      </div>
      <div className="mt-1.5 text-2xl font-semibold tabular-nums text-neutral-900 dark:text-neutral-50">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-neutral-400 dark:text-neutral-500">{sub}</div>}
    </Card>
  )
}
