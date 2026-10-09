import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Compass, LogIn } from 'lucide-react'
import '../styles/AuthPage.css'

function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    login({
      id: 1,
      name: 'Алексей Иванов',
      email: formData.email,
      role: 'Геолог',
    })
    navigate('/dashboard')
  }

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-header">
          <Compass size={48} className="auth-logo" />
          <h1>GeoLens</h1>
          <p>Интеллектуальная система поддержки принятия решений</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <h2>Вход в систему</h2>

          <div className="form-group">
            <label className="label">Email</label>
            <input
              type="email"
              className="input"
              placeholder="your@email.com"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label className="label">Пароль</label>
            <input
              type="password"
              className="input"
              placeholder="••••••••"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
            />
          </div>

          <button type="submit" className="btn btn-primary auth-btn">
            <LogIn size={18} />
            Войти
          </button>

          <div className="auth-footer">
            Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
          </div>
        </form>
      </div>
    </div>
  )
}

export default LoginPage