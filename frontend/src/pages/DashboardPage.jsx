import {
  TrendingUp,
  MapPin,
  Database,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts'
import '../styles/DashboardPage.css'

function DashboardPage() {
  const stats = [
    { title: 'Активных участков', value: '12', change: '+2', trend: 'up', icon: MapPin, color: '#667eea' },
    { title: 'Точек данных', value: '2,847', change: '+156', trend: 'up', icon: Database, color: '#764ba2' },
    { title: 'Моделей ML', value: '8', change: '+1', trend: 'up', icon: BarChart3, color: '#f093fb' },
    { title: 'Прогноз ресурсов', value: '₽2.4B', change: '-5%', trend: 'down', icon: TrendingUp, color: '#4facfe' },
  ]

  const chartData = [
    { month: 'Янв', value: 400 },
    { month: 'Фев', value: 300 },
    { month: 'Мар', value: 600 },
    { month: 'Апр', value: 800 },
    { month: 'Май', value: 700 },
    { month: 'Июн', value: 900 },
  ]

  const barData = [
    { name: 'Au', value: 65 },
    { name: 'Cu', value: 45 },
    { name: 'Fe', value: 80 },
    { name: 'Ag', value: 35 },
  ]

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Обзор геологоразведочных работ</p>
      </div>

      <div className="stats-grid">
        {stats.map((stat, index) => {
          const Icon = stat.icon
          return (
            <div key={index} className="stat-card">
              <div className="stat-header">
                <div className="stat-icon" style={{ background: stat.color }}>
                  <Icon size={24} />
                </div>
                <div className={`stat-trend ${stat.trend}`}>
                  {stat.trend === 'up' ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                  {stat.change}
                </div>
              </div>
              <div className="stat-value">{stat.value}</div>
              <div className="stat-title">{stat.title}</div>
            </div>
          )
        })}
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3>Динамика разведки</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3040" />
              <XAxis dataKey="month" stroke="#a0aec0" />
              <YAxis stroke="#a0aec0" />
              <Tooltip contentStyle={{ background: '#1a1f2e', border: '1px solid #2a3040', borderRadius: '8px' }} />
              <Line type="monotone" dataKey="value" stroke="#667eea" strokeWidth={2} dot={{ fill: '#667eea', r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Концентрация минералов</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a3040" />
              <XAxis dataKey="name" stroke="#a0aec0" />
              <YAxis stroke="#a0aec0" />
              <Tooltip contentStyle={{ background: '#1a1f2e', border: '1px solid #2a3040', borderRadius: '8px' }} />
              <Bar dataKey="value" fill="#764ba2" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="recent-activity">
        <h3>Последняя активность</h3>
        <div className="activity-list">
          <div className="activity-item">
            <div className="activity-icon" style={{ background: '#667eea' }}><MapPin size={16} /></div>
            <div className="activity-content">
              <div className="activity-title">Добавлен новый участок "Северный-3"</div>
              <div className="activity-time">2 часа назад</div>
            </div>
          </div>
          <div className="activity-item">
            <div className="activity-icon" style={{ background: '#764ba2' }}><Database size={16} /></div>
            <div className="activity-content">
              <div className="activity-title">Загружено 24 новых пробы</div>
              <div className="activity-time">5 часов назад</div>
            </div>
          </div>
          <div className="activity-item">
            <div className="activity-icon" style={{ background: '#f093fb' }}><BarChart3 size={16} /></div>
            <div className="activity-content">
              <div className="activity-title">Обновлена модель прогнозирования</div>
              <div className="activity-time">Вчера</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DashboardPage