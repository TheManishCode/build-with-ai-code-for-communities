import { useId, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'

export interface LineSeries {
  name: string
  color: string
  values: number[] // aligned with `xLabels`
}

/** A small, dependency-free SVG line chart -- change-over-an-ordered-dimension is a line
 * chart's job (see dataviz skill choosing-a-form). Ships a legend (>= 2 series), a hover
 * crosshair that reads every series at once, and value-at-the-end direct labels. */
export function LineChart({
  xLabels,
  series,
  yFormatter = (v) => `${Math.round(v * 100)}%`,
}: {
  xLabels: (string | number)[]
  series: LineSeries[]
  yFormatter?: (v: number) => string
}) {
  const clipId = useId()
  const [hoverIdx, setHoverIdx] = useState<number | null>(null)
  const reduceMotion = useReducedMotion()

  const width = 560
  const height = 240
  const padding = { top: 16, right: 16, bottom: 28, left: 36 }
  const plotW = width - padding.left - padding.right
  const plotH = height - padding.top - padding.bottom

  const allValues = series.flatMap((s) => s.values)
  const yMax = Math.max(...allValues, 0.01)
  const yMin = 0

  const xStep = xLabels.length > 1 ? plotW / (xLabels.length - 1) : 0
  const xAt = (i: number) => padding.left + i * xStep
  const yAt = (v: number) => padding.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH

  const gridSteps = [0, 0.25, 0.5, 0.75, 1].map((f) => yMin + f * (yMax - yMin))

  const pathFor = (values: number[]) => values.map((v, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${yAt(v)}`).join(' ')

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Line chart">
        <defs>
          <clipPath id={clipId}>
            <rect x={padding.left} y={padding.top} width={plotW} height={plotH} />
          </clipPath>
        </defs>

        {/* gridlines -- recessive hairlines, one step off the surface */}
        {gridSteps.map((v) => (
          <g key={v}>
            <line
              x1={padding.left}
              x2={width - padding.right}
              y1={yAt(v)}
              y2={yAt(v)}
              stroke="currentColor"
              strokeWidth={1}
              className="text-stone-200 dark:text-stone-800"
            />
            <text x={padding.left - 8} y={yAt(v)} textAnchor="end" dominantBaseline="middle" className="fill-stone-400 text-[9px]">
              {yFormatter(v)}
            </text>
          </g>
        ))}

        {/* x-axis labels */}
        {xLabels.map((label, i) => (
          <text key={i} x={xAt(i)} y={height - 8} textAnchor="middle" className="fill-stone-400 text-[9px]">
            {label}
          </text>
        ))}

        {/* hover crosshair */}
        {hoverIdx !== null && (
          <line
            x1={xAt(hoverIdx)}
            x2={xAt(hoverIdx)}
            y1={padding.top}
            y2={padding.top + plotH}
            stroke="currentColor"
            strokeWidth={1}
            className="text-stone-300 dark:text-stone-700"
          />
        )}

        {/* series lines -- drawn in with a stroke-dashoffset reveal on mount */}
        <g clipPath={`url(#${clipId})`}>
          {series.map((s) => {
            const d = pathFor(s.values)
            return (
              <motion.path
                key={s.name}
                d={d}
                fill="none"
                stroke={s.color}
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
                initial={reduceMotion ? undefined : { pathLength: 0 }}
                animate={reduceMotion ? undefined : { pathLength: 1 }}
                transition={{ duration: 0.7, ease: 'easeOut' }}
              />
            )
          })}
        </g>

        {/* markers + end labels */}
        {series.map((s) =>
          s.values.map((v, i) => {
            const isEnd = i === s.values.length - 1
            const isHover = hoverIdx === i
            return (
              <g key={`${s.name}-${i}`}>
                <circle
                  cx={xAt(i)}
                  cy={yAt(v)}
                  r={isHover || isEnd ? 5 : 3.5}
                  fill={s.color}
                  strokeWidth={2}
                  className="stroke-stone-50 dark:stroke-stone-900"
                />
                {isEnd && (
                  <text x={xAt(i) + 7} y={yAt(v)} dominantBaseline="middle" className="fill-stone-700 text-[10px] font-semibold dark:fill-stone-200">
                    {yFormatter(v)}
                  </text>
                )}
              </g>
            )
          }),
        )}

        {/* hit targets -- one per x position, bigger than the marks, hoverable/focusable */}
        {xLabels.map((_, i) => (
          <rect
            key={i}
            x={xAt(i) - xStep / 2}
            y={padding.top}
            width={xStep || plotW}
            height={plotH}
            fill="transparent"
            onMouseEnter={() => setHoverIdx(i)}
            onMouseLeave={() => setHoverIdx(null)}
            onFocus={() => setHoverIdx(i)}
            onBlur={() => setHoverIdx(null)}
            tabIndex={0}
            role="button"
            aria-label={`${xLabels[i]}: ${series.map((s) => `${s.name} ${yFormatter(s.values[i])}`).join(', ')}`}
          />
        ))}
      </svg>

      {/* legend -- required for >= 2 series */}
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
        {series.map((s) => (
          <span key={s.name} className="flex items-center gap-1.5 text-xs text-stone-600 dark:text-stone-400">
            <span className="h-0.5 w-3 rounded-full" style={{ backgroundColor: s.color }} />
            {s.name}
          </span>
        ))}
      </div>

      {/* tooltip -- readout of every series at the hovered x, reachable by keyboard focus too */}
      {hoverIdx !== null && (
        <div className="mt-2 rounded-md border border-stone-200 bg-stone-50 px-3 py-2 text-xs dark:border-stone-800 dark:bg-stone-800">
          <div className="mb-1 font-medium text-stone-700 dark:text-stone-200">{xLabels[hoverIdx]}</div>
          <div className="flex flex-col gap-0.5">
            {series.map((s) => (
              <div key={s.name} className="flex items-center justify-between gap-4">
                <span className="flex items-center gap-1.5 text-stone-500 dark:text-stone-400">
                  <span className="h-0.5 w-3 rounded-full" style={{ backgroundColor: s.color }} />
                  {s.name}
                </span>
                <span className="font-medium tabular-nums text-stone-900 dark:text-stone-50">{yFormatter(s.values[hoverIdx])}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
