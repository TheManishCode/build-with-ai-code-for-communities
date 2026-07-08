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
  return (
    <div className="flex flex-col gap-2.5" role="img" aria-label="Bar chart">
      {data.map((d) => {
        const pct = (d.value / max) * 100
        return (
          <div key={d.label} className="group flex items-center gap-3 text-sm">
            <span className="w-24 shrink-0 truncate capitalize text-neutral-600 dark:text-neutral-400" title={d.label}>
              {d.label}
            </span>
            <div className="h-2 flex-1 rounded-full bg-neutral-100 dark:bg-neutral-800">
              <div
                className="h-2 rounded-full transition-[width] group-hover:brightness-110"
                style={{ width: `${pct}%`, backgroundColor: d.color }}
                title={`${d.label}: ${d.formattedValue}`}
              />
            </div>
            <span className="w-10 shrink-0 text-right tabular-nums text-neutral-500 dark:text-neutral-400">{d.formattedValue}</span>
          </div>
        )
      })}
    </div>
  )
}
