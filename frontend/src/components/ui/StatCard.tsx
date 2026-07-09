import type { ReactNode } from 'react'

interface MetricGridProps {
  children: ReactNode
  style?: React.CSSProperties
}

export function MetricGrid({ children, style }: MetricGridProps) {
  return <div className="metric-grid" style={style}>{children}</div>
}

interface MetricProps {
  label: string
  value: string | number
  sub?: string
  valueColor?: string
}

export function Metric({ label, value, sub, valueColor }: MetricProps) {
  return (
    <div className="metric-cell">
      <span className="metric-label">{label}</span>
      <span className="metric-value" style={valueColor ? { color: valueColor } : undefined}>{value}</span>
      {sub && <span className="metric-sub">{sub}</span>}
    </div>
  )
}

interface HeroMetricProps {
  label: string
  value: string | number
  sub?: string
  icon?: ReactNode
}

export function HeroMetric({ label, value, sub, icon }: HeroMetricProps) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-text-tertiary)' }}>
        {icon}
        <span className="metric-label">{label}</span>
      </div>
      <div className="metric-hero-value" style={{ marginTop: 6 }}>{value}</div>
      {sub && <div className="metric-sub" style={{ marginTop: 6 }}>{sub}</div>}
    </div>
  )
}
