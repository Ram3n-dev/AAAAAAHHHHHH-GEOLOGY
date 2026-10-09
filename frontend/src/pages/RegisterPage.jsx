import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Compass, UserPlus } from 'lucide-react'
import '../styles/AuthPage.css'

function RegisterPage() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (formData.password !== formData.confirmPassword) {
      alert('Пароли не совпадают')
      return
    }

    login({
      id: 1,
      name: formData.name,
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
          <h2>Регистрация</h2>

          <div className="form-group">
            <label className="label">Имя</label>
            <input
              type="text"
              className="input"
              placeholder="Иван Иванов"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>

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

          <div className="form-group">
            <label className="label">Подтвердите пароль</label>
            <input
              type="password"
              className="input"
              placeholder="••••••••"
              value={formData.confirmPassword}
              onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
              required
            />
          </div>

          <button type="submit" className="btn btn-primary auth-btn">
            <UserPlus size={18} />
            Зарегистрироваться
          </button>

          <div className="auth-footer">
            Уже есть аккаунт? <Link to="/login">Войти</Link>
          </div>
        </form>
      </div>
    </div>
  )
}

export default RegisterPage