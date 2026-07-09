import type { ReactNode } from 'react'

/** A register leaf -- flat paper, not a floating widget. Definition comes from a hairline
 * border and a background step off the page, not a drop shadow. */
export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-md border border-stone-200 bg-stone-50 dark:border-stone-800 dark:bg-stone-900 ${className}`}>
      {children}
    </div>
  )
}
