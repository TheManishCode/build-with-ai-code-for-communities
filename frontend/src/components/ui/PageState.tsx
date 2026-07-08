import { AlertTriangle, Loader2 } from 'lucide-react'

export function Loading({ label }: { label: string }) {
  return (
    <div className="mx-auto flex max-w-3xl items-center gap-2 p-6 text-sm text-neutral-500 dark:text-neutral-400">
      <Loader2 size={16} className="animate-spin" aria-hidden="true" />
      {label}
    </div>
  )
}

export function ErrorState({ label }: { label: string }) {
  return (
    <div className="mx-auto flex max-w-3xl items-start gap-2 p-6 text-sm text-critical" role="alert">
      <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
      {label}
    </div>
  )
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">{title}</h2>
      {subtitle && <p className="mt-0.5 text-sm text-neutral-500 dark:text-neutral-400">{subtitle}</p>}
    </div>
  )
}
