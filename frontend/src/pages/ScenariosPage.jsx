import { GitBranch, Play, Pause, CheckCircle } from 'lucide-react'
import '../styles/PlaceholderPage.css'

function ScenariosPage() {
  const scenarios = [
    { name: 'Базовый сценарий', status: 'active', confidence: '87%' },
    { name: 'Оптимистичный', status: 'inactive', confidence: '72%' },
    { name: 'Пессимистичный', status: 'inactive', confidence: '65%' },
  ]

  return (
    <div className="placeholder-page">
      <div className="page-header">
        <h1>Сценарии</h1>
        <p>Моделирование различных сценариев разработки</p>
      </div>

      <div className="scenarios-grid">
        {scenarios.map((scenario, index) => (
          <div key={index} className="scenario-card">
            <GitBranch size={32} className="scenario-icon" />
            <h3>{scenario.name}</h3>
            <div className={`scenario-status status-${scenario.status}`}>
              {scenario.status === 'active' ? (<><Play size={16} />Активен</>) : (<><Pause size={16} />Неактивен</>)}
            </div>
            <div className="scenario-confidence">
              <CheckCircle size={16} />
              Достоверность: {scenario.confidence}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ScenariosPage