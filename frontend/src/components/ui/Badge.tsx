import type { CSSProperties } from 'react'
import { themeColor } from '../../theme'

/** A theme-category chip (water/road/school/...). Color is fixed per category -- see theme.ts.
 * Carries a small solid dot ahead of the label so the category still reads by shape/position
 * even before color registers (helps at a glance in a long ranked list). */
export function ThemeBadge({ theme, className = '' }: { theme: string; className?: string }) {
  const c = themeColor(theme)
  const style = {
    '--chip-bg': c.bg,
    '--chip-fg': c.fg,
    '--chip-bg-dark': c.bgDark,
    '--chip-fg-dark': c.fgDark,
    '--chip-dot': c.swatch,
  } as CSSProperties
  return (
    <span
      style={style}
      className={`theme-chip inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${className}`}
    >
      <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: 'var(--chip-dot)' }} />
      {theme}
    </span>
  )
}

const STATUS_CLASSES: Record<'good' | 'warning' | 'critical' | 'neutral', string> = {
  good: 'bg-good/10 text-good dark:bg-good/20',
  warning: 'bg-warning/10 text-warning dark:bg-warning/20',
  critical: 'bg-critical/10 text-critical dark:bg-critical/20',
  neutral: 'bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-300',
}

/** A status pill -- always icon+label from the caller, never color alone (see theme.ts). */
export function StatusBadge({
  tone,
  children,
  className = '',
}: {
  tone: 'good' | 'warning' | 'critical' | 'neutral'
  children: React.ReactNode
  className?: string
}) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_CLASSES[tone]} ${className}`}>
      {children}
    </span>
  )
}
