import { Bell, Search } from 'lucide-react'
import '../styles/Header.css'

function Header() {
  return (
    <header className="header">
      <div className="header-search">
        <Search size={18} />
        <input
          type="text"
          placeholder="Поиск участков, данных, отчётов..."
          className="search-input"
        />
      </div>

      <div className="header-actions">
        <button className="icon-btn">
          <Bell size={20} />
          <span className="badge">3</span>
        </button>
      </div>
    </header>
  )
}

export default Header