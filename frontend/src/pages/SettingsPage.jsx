import { User, Bell, Shield, Database } from 'lucide-react'
import '../styles/PlaceholderPage.css'

function SettingsPage() {
  return (
    <div className="placeholder-page">
      <div className="page-header">
        <h1>Настройки</h1>
        <p>Конфигурация системы и профиля</p>
      </div>

      <div className="settings-sections">
        <div className="settings-card">
          <User size={24} />
          <h3>Профиль</h3>
          <p>Управление личной информацией</p>
        </div>
        <div className="settings-card">
          <Bell size={24} />
          <h3>Уведомления</h3>
          <p>Настройка уведомлений системы</p>
        </div>
        <div className="settings-card">
          <Shield size={24} />
          <h3>Безопасность</h3>
          <p>Пароли и аутентификация</p>
        </div>
        <div className="settings-card">
          <Database size={24} />
          <h3>Данные</h3>
          <p>Управление данными и резервными копиями</p>
        </div>
      </div>
    </div>
  )
}

export default SettingsPage