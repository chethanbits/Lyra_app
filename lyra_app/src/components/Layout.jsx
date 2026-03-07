import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import './Layout.css'

const tabs = [
  { path: '/app/home', label: 'Home', icon: '◇' },
  { path: '/app/planner', label: 'Planner', icon: '◈' },
  { path: '/app/calendar', label: 'Calendar', icon: '▣' },
  { path: '/app/festivals', label: 'Festivals', icon: '🪔' },
  { path: '/app/settings', label: 'Settings', icon: '⚙' },
]

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <div className="layout">
      <main className="layout-main">
        <Outlet />
      </main>
      <nav className="bottom-nav">
        {tabs.map(({ path, label, icon }) => (
          <button
            key={path}
            type="button"
            className={`nav-item ${location.pathname === path ? 'active' : ''}`}
            onClick={() => navigate(path)}
            aria-current={location.pathname === path ? 'page' : undefined}
          >
            <span className="nav-icon">{icon}</span>
            <span className="nav-label">{label}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}
