import { STATUS, scoreStatus } from '../../theme'

const STATUS_HEX: Record<'good' | 'warning' | 'critical', string> = STATUS

/** A severity meter: fill carries the status color, unfilled track is a lighter step of the
 * same ramp so state reads across the whole bar (not just the filled portion). */
export function Meter({ value, className = '' }: { value: number; className?: string }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100)
  const status = scoreStatus(value)
  const color = STATUS_HEX[status]
  return (
    <div
      className={`h-2 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800 ${className}`}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="h-full rounded-full transition-[width]" style={{ width: `${pct}%`, backgroundColor: color }} />
    </div>
  )
}
