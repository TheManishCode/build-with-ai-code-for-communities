import type { CSSProperties } from 'react'
import { themeColor } from '../../theme'

/** A theme-category chip (water/road/school/...). Color is fixed per category -- see theme.ts. */
export function ThemeBadge({ theme, className = '' }: { theme: string; className?: string }) {
  const c = themeColor(theme)
  const style = {
    '--chip-bg': c.bg,
    '--chip-fg': c.fg,
    '--chip-bg-dark': c.bgDark,
    '--chip-fg-dark': c.fgDark,
  } as CSSProperties
  return (
    <span
      style={style}
      className={`theme-chip inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${className}`}
    >
      {theme}
    </span>
  )
}

const STATUS_CLASSES: Record<'good' | 'warning' | 'critical' | 'neutral', string> = {
  good: 'bg-good/10 text-good dark:bg-good/15',
  warning: 'bg-warning/15 text-amber-800 dark:bg-warning/20 dark:text-amber-300',
  critical: 'bg-critical/10 text-critical dark:bg-critical/15',
  neutral: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
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
