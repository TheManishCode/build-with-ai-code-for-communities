import { motion, useReducedMotion } from 'motion/react'

interface BarDatum {
  label: string
  value: number
  color: string
  formattedValue: string
}

/** Horizontal bar chart -- ranked categorical comparison. Each bar carries its own adjacent
 * label (category + value), so no shared legend box is needed (see dataviz skill: a legend
 * exists to substitute for direct labels, not alongside them). Mark spec: 8px thick,
 * 4px rounded end, square at the baseline. */
export function BarChart({ data }: { data: BarDatum[] }) {
  const max = Math.max(...data.map((d) => d.value), 1)
  const reduceMotion = useReducedMotion()
  return (
    <div className="flex flex-col gap-2.5" role="img" aria-label="Bar chart">
      {data.map((d, i) => {
        const pct = (d.value / max) * 100
        return (
          <div key={d.label} className="group flex items-center gap-3 text-sm">
            <span className="w-24 shrink-0 truncate capitalize text-stone-600 dark:text-stone-400" title={d.label}>
              {d.label}
            </span>
            <div className="h-2 flex-1 rounded-full bg-stone-100 dark:bg-stone-800">
              <motion.div
                className="h-2 rounded-full group-hover:brightness-110"
                style={{ backgroundColor: d.color }}
                initial={{ width: reduceMotion ? `${pct}%` : 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ type: 'spring', stiffness: 110, damping: 22, delay: reduceMotion ? 0 : i * 0.04 }}
                title={`${d.label}: ${d.formattedValue}`}
              />
            </div>
            <span className="w-10 shrink-0 text-right tabular-nums text-stone-500 dark:text-stone-400">{d.formattedValue}</span>
          </div>
        )
      })}
    </div>
  )
}
