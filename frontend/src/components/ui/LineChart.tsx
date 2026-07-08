import { useId, useState } from 'react'

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
              className="text-neutral-200 dark:text-neutral-800"
            />
            <text x={padding.left - 8} y={yAt(v)} textAnchor="end" dominantBaseline="middle" className="fill-neutral-400 text-[9px]">
              {yFormatter(v)}
            </text>
          </g>
        ))}

        {/* x-axis labels */}
        {xLabels.map((label, i) => (
          <text key={i} x={xAt(i)} y={height - 8} textAnchor="middle" className="fill-neutral-400 text-[9px]">
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
            className="text-neutral-300 dark:text-neutral-700"
          />
        )}

        {/* series lines */}
        <g clipPath={`url(#${clipId})`}>
          {series.map((s) => (
            <path key={s.name} d={pathFor(s.values)} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          ))}
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
                  r={isHover ? 5 : 4}
                  fill={s.color}
                  stroke="var(--surface-ring, white)"
                  strokeWidth={2}
                  className="stroke-white dark:stroke-neutral-900"
                />
                {isEnd && (
                  <text x={xAt(i) + 6} y={yAt(v)} dominantBaseline="middle" className="fill-neutral-600 text-[10px] font-medium dark:fill-neutral-300">
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
          <span key={s.name} className="flex items-center gap-1.5 text-xs text-neutral-600 dark:text-neutral-400">
            <span className="h-0.5 w-3 rounded-full" style={{ backgroundColor: s.color }} />
            {s.name}
          </span>
        ))}
      </div>

      {/* tooltip -- readout of every series at the hovered x, reachable by keyboard focus too */}
      {hoverIdx !== null && (
        <div className="mt-2 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs dark:border-neutral-800 dark:bg-neutral-800">
          <div className="mb-1 font-medium text-neutral-700 dark:text-neutral-200">{xLabels[hoverIdx]}</div>
          <div className="flex flex-col gap-0.5">
            {series.map((s) => (
              <div key={s.name} className="flex items-center justify-between gap-4">
                <span className="flex items-center gap-1.5 text-neutral-500 dark:text-neutral-400">
                  <span className="h-0.5 w-3 rounded-full" style={{ backgroundColor: s.color }} />
                  {s.name}
                </span>
                <span className="font-medium tabular-nums text-neutral-900 dark:text-neutral-50">{yFormatter(s.values[hoverIdx])}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
