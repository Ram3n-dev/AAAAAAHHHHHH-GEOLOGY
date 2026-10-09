import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Map,
  Database,
  BarChart3,
  Brain,
  FileText,
  GitBranch,
  Settings,
  Compass
} from 'lucide-react'
import '../styles/Sidebar.css'

function Sidebar() {
  const menuItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/map', icon: Map, label: 'Карта' },
    { path: '/data', icon: Database, label: 'Данные' },
    { path: '/analysis', icon: BarChart3, label: 'Анализ' },
    { path: '/models', icon: Brain, label: 'Модели' },
    { path: '/reports', icon: FileText, label: 'Отчёты' },
    { path: '/scenarios', icon: GitBranch, label: 'Сценарии' },
    { path: '/settings', icon: Settings, label: 'Настройки' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <Compass className="sidebar-logo" size={32} />
        <span className="sidebar-title">GeoLens</span>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? 'active' : ''}`
              }
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="user-info">
          <div className="user-avatar">АИ</div>
          <div className="user-details">
            <div className="user-name">Алексей Иванов</div>
            <div className="user-role">Геолог</div>
          </div>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar