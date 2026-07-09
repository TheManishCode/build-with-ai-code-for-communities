import { motion, useReducedMotion } from 'motion/react'
import { STATUS, scoreStatus } from '../../theme'

const STATUS_HEX: Record<'good' | 'warning' | 'critical', string> = STATUS

// Matches the good/warning/critical cutoffs in scoreStatus() -- shown as ticks so a reader
// can place a score in absolute terms, not just guess from fill length.
const THRESHOLDS = [0.4, 0.7]

/** A severity meter: fill carries the status color, unfilled track is a lighter step of the
 * same ramp so state reads across the whole bar (not just the filled portion). Threshold
 * ticks mark where "warning" and "critical" begin. */
export function Meter({ value, className = '' }: { value: number; className?: string }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100)
  const status = scoreStatus(value)
  const color = STATUS_HEX[status]
  const reduceMotion = useReducedMotion()
  return (
    <div
      className={`relative h-2 w-full overflow-hidden rounded-full bg-stone-200 dark:bg-stone-800 ${className}`}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <motion.div
        className="h-full rounded-full"
        style={{ backgroundColor: color }}
        initial={{ width: reduceMotion ? `${pct}%` : 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ type: 'spring', stiffness: 120, damping: 20 }}
      />
      {THRESHOLDS.map((t) => (
        <span
          key={t}
          className="absolute top-0 h-full w-px bg-stone-50/70 dark:bg-stone-950/50"
          style={{ left: `${t * 100}%` }}
          aria-hidden="true"
        />
      ))}
    </div>
  )
}
