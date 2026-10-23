import { Brain, Cpu, TrendingUp, CheckCircle } from 'lucide-react'
import '../styles/PlaceholderPage.css'

function ModelsPage() {
  const models = [
    { name: 'Random Forest', status: 'trained', accuracy: '94.2%' },
    { name: 'Neural Network', status: 'training', accuracy: '-' },
    { name: 'SVM Classifier', status: 'trained', accuracy: '89.7%' },
  ]

  return (
    <div className="placeholder-page">
      <div className="page-header">
        <h1>Модели машинного обучения</h1>
        <p>Управление и обучение ML моделей</p>
      </div>

      <div className="models-grid">
        {models.map((model, index) => (
          <div key={index} className="model-card">
            <Brain size={32} className="model-icon" />
            <h3>{model.name}</h3>
            <div className={`model-status status-${model.status}`}>
              {model.status === 'trained' ? (<><CheckCircle size={16} />Обучена</>) : (<><Cpu size={16} />Обучение...</>)}
            </div>
            {model.accuracy !== '-' && (
              <div className="model-accuracy">
                <TrendingUp size={16} />
                Accuracy: {model.accuracy}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default ModelsPage