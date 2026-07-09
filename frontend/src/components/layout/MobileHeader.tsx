import { Menu } from 'lucide-react'

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
      <span style={{
        fontSize: 'var(--text-sm)',
        fontWeight: 700,
        color: 'var(--color-text-primary)',
      }}>
        MPLADS Portal
      </span>
      <div style={{ width: 36 }} />
    </div>
  )
}
