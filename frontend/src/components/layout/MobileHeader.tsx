import { Menu, Shield } from 'lucide-react'

interface MobileHeaderProps {
  onMenuToggle: () => void
}

export function MobileHeader({ onMenuToggle }: MobileHeaderProps) {
  return (
    <div className="mobile-header">
      <button
        onClick={onMenuToggle}
        className="btn btn-ghost"
        aria-label="Toggle navigation menu"
      >
        <Menu size={20} />
      </button>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{
          width: 26,
          height: 26,
          borderRadius: 'var(--radius-sm)',
          background: 'var(--color-accent)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <Shield size={14} color="#17130a" strokeWidth={2.5} />
        </div>
        <span style={{
          fontSize: 'var(--text-sm)',
          fontWeight: 700,
          color: 'var(--color-text-primary)',
        }}>
          Civic Intelligence
        </span>
      </div>
      <div style={{ width: 36 }} />
    </div>
  )
}
