import { motion } from 'framer-motion'
import { AlertCircle, Inbox } from 'lucide-react'
import type { ReactNode } from 'react'

/* ─── Loading Skeleton ────────────────────────────────────────── */
export function LoadingSkeleton({ lines = 3, height = 120 }: { lines?: number; height?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="loading-skeleton"
          style={{ height: i === 0 ? height : 48, width: '100%' }}
        />
      ))}
    </div>
  )
}

/* ─── Stat Card Skeleton ──────────────────────────────────────── */
export function StatsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="metric-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="metric-cell">
          <div className="loading-skeleton" style={{ width: 60, height: 28, marginBottom: 8 }} />
          <div className="loading-skeleton" style={{ width: 90, height: 11 }} />
        </div>
      ))}
    </div>
  )
}

/* ─── Spinner ─────────────────────────────────────────────────── */
export function Spinner({ size = 24 }: { size?: number }) {
  return (
    <div className="spinner" style={{ width: size, height: size }} />
  )
}

/* ─── Loading State ───────────────────────────────────────────── */
export function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-16) var(--space-6)',
        gap: 'var(--space-4)',
      }}
    >
      <Spinner size={32} />
      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-tertiary)' }}>
        {message}
      </p>
    </motion.div>
  )
}

/* ─── Error State ─────────────────────────────────────────────── */
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      className="error-banner"
      role="alert"
    >
      <AlertCircle size={18} style={{ flexShrink: 0, marginTop: 1 }} />
      <div style={{ flex: 1 }}>
        <p>{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="btn btn-sm btn-secondary"
            style={{ marginTop: 'var(--space-3)' }}
          >
            Try again
          </button>
        )}
      </div>
    </motion.div>
  )
}

/* ─── Empty State ─────────────────────────────────────────────── */
export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="empty-state"
    >
      <div className="empty-state-icon">
        {icon || <Inbox size={48} />}
      </div>
      <div className="empty-state-title">{title}</div>
      {description && <div className="empty-state-text">{description}</div>}
      {action && <div style={{ marginTop: 'var(--space-4)' }}>{action}</div>}
    </motion.div>
  )
}
