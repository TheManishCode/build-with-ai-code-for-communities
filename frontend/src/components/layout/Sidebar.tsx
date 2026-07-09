import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  ListOrdered,
  Map,
  Wallet,
  FlaskConical,
  Search,
  Shield,
  FileText,
  MessageSquarePlus,
  Bot,
} from 'lucide-react'

const NAV_SECTIONS = [
  {
    label: 'Overview',
    links: [
      { to: '/', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/report', label: 'AI Report', icon: FileText },
    ],
  },
  {
    label: 'Analysis',
    links: [
      { to: '/priorities', label: 'Ranked Priorities', icon: ListOrdered },
      { to: '/map', label: 'Constituency Map', icon: Map },
      { to: '/budget', label: 'Budget Simulator', icon: Wallet },
      { to: '/backtest', label: 'Model Backtest', icon: FlaskConical },
    ],
  },
  {
    label: 'Public',
    links: [
      { to: '/report-issue', label: 'Report an Issue', icon: MessageSquarePlus },
      { to: '/assistant', label: 'Ask for Help', icon: Bot },
      { to: '/status', label: 'Check My Report', icon: Search },
      { to: '/transparency', label: 'Transparency', icon: Shield },
    ],
  },
]

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  return (
    <nav
      className={`app-sidebar ${isOpen ? 'open' : ''}`}
      aria-label="Main navigation"
    >
      <div className="sidebar-brand">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 28,
            height: 28,
            borderRadius: 'var(--radius-sm)',
            background: 'var(--color-accent)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            <Shield size={15} color="#17130a" strokeWidth={2.5} />
          </div>
          <div>
            <div className="sidebar-brand-name">Civic Intelligence</div>
            <div className="sidebar-brand-sub">Bagalkot, Karnataka</div>
          </div>
        </div>
      </div>

      {NAV_SECTIONS.map((section) => (
        <div className="sidebar-section" key={section.label}>
          <div className="sidebar-section-label">{section.label}</div>
          {section.links.map((link) => {
            const Icon = link.icon

            return (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === '/'}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
                onClick={onClose}
              >
                <Icon size={17} />
                <span>{link.label}</span>
              </NavLink>
            )
          })}
        </div>
      ))}

      <div style={{ flex: 1 }} />

      <div style={{
        padding: 'var(--space-3) var(--space-5) 0',
        borderTop: '1px solid var(--color-border-default)',
        marginTop: 'var(--space-4)',
        paddingTop: 'var(--space-4)',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
          fontSize: 'var(--text-xs)',
          color: 'var(--color-text-muted)',
        }}>
          <div className="pulse-dot" />
          <span>Data pipeline active</span>
        </div>
      </div>
    </nav>
  )
}
