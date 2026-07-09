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
} from 'lucide-react'

const NAV_SECTIONS = [
  {
    label: 'Overview',
    links: [
      { to: '/', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/report', label: 'Development Report', icon: FileText },
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
        <div className="sidebar-brand-name">MPLADS Portal</div>
        <div className="sidebar-brand-sub">Bagalkot Constituency, Karnataka</div>
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
    </nav>
  )
}
