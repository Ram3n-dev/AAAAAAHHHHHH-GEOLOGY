import { useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { Brain, TrendingUp, Target, Zap } from 'lucide-react'
import '../styles/AnalysisPage.css'

function AnalysisPage() {
  const [selectedAnalysis, setSelectedAnalysis] = useState('correlation')

  const correlationData = [
    { x: 10, y: 15, z: 200 },
    { x: 20, y: 25, z: 300 },
    { x: 30, y: 35, z: 250 },
    { x: 40, y: 45, z: 400 },
    { x: 50, y: 55, z: 350 },
  ]

  const distributionData = [
    { range: '0-10', count: 24 },
    { range: '10-20', count: 45 },
    { range: '20-30', count: 67 },
    { range: '30-40', count: 52 },
    { range: '40-50', count: 38 },
  ]

  const trendData = [
    { month: 'Янв', actual: 400, predicted: 380 },
    { month: 'Фев', actual: 300, predicted: 320 },
    { month: 'Мар', actual: 600, predicted: 580 },
    { month: 'Апр', actual: 800, predicted: 750 },
    { month: 'Май', actual: 700, predicted: 720 },
    { month: 'Июн', actual: 900, predicted: 880 },
  ]

  const analysisTypes = [
    { id: 'correlation', label: 'Корреляционный анализ', icon: Target },
    { id: 'distribution', label: 'Распределение', icon: BarChart },
    { id: 'trend', label: 'Тренды', icon: TrendingUp },
    { id: 'ml', label: 'ML прогнозы', icon: Brain },
  ]

  return (
    <div className="analysis-page">
      <div className="page-header">
        <h1>Анализ данных</h1>
        <p>Статистический анализ и машинное обучение</p>
      </div>

      <div className="analysis-tabs">
        {analysisTypes.map((type) => {
          const Icon = type.icon
          return (
            <button
              key={type.id}
              className={`analysis-tab ${selectedAnalysis === type.id ? 'active' : ''}`}
              onClick={() => setSelectedAnalysis(type.id)}
            >
              <Icon size={18} />
              {type.label}
            </button>
          )
        })}
      </div>

      <div className="analysis-content">
        {selectedAnalysis === 'correlation' && (
          <>
            <div className="analysis-card">
              <h3>Корреляция концентрации минералов</h3>
              <ResponsiveContainer width="100%" height={400}>
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a3040" />
                  <XAxis type="number" dataKey="x" name="Глубина" stroke="#a0aec0" />
                  <YAxis type="number" dataKey="y" name="Концентрация" stroke="#a0aec0" />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ background: '#1a1f2e', border: '1px solid #2a3040', borderRadius: '8px' }} />
                  <Scatter name="Пробы" data={correlationData} fill="#667eea" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>

            <div className="analysis-insights">
              <div className="insight-card">
                <Zap size={24} />
                <div>
                  <h4>Сильная корреляция</h4>
                  <p>Коэффициент корреляции: 0.87</p>
                </div>
              </div>
              <div className="insight-card">
                <Target size={24} />
                <div>
                  <h4>Оптимальная глубина</h4>
                  <p>Максимальная концентрация на 40-50 м</p>
                </div>
              </div>
            </div>
          </>
        )}

        {selectedAnalysis === 'distribution' && (
          <div className="analysis-card">
            <h3>Распределение концентраций</h3>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={distributionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3040" />
                <XAxis dataKey="range" stroke="#a0aec0" />
                <YAxis stroke="#a0aec0" />
                <Tooltip contentStyle={{ background: '#1a1f2e', border: '1px solid #2a3040', borderRadius: '8px' }} />
                <Bar dataKey="count" fill="#764ba2" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {selectedAnalysis === 'trend' && (
          <div className="analysis-card">
            <h3>Тренды добычи</h3>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3040" />
                <XAxis dataKey="month" stroke="#a0aec0" />
                <YAxis stroke="#a0aec0" />
                <Tooltip contentStyle={{ background: '#1a1f2e', border: '1px solid #2a3040', borderRadius: '8px' }} />
                <Legend />
                <Line type="monotone" dataKey="actual" stroke="#667eea" strokeWidth={2} name="Факт" />
                <Line type="monotone" dataKey="predicted" stroke="#f093fb" strokeWidth={2} strokeDasharray="5 5" name="Прогноз" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {selectedAnalysis === 'ml' && (
          <div className="ml-section">
            <div className="ml-card">
              <Brain size={48} />
              <h3>Модель прогнозирования</h3>
              <p>Random Forest Classifier</p>
              <div className="ml-metrics">
                <div className="metric">
                  <div className="metric-value">94.2%</div>
                  <div className="metric-label">Accuracy</div>
                </div>
                <div className="metric">
                  <div className="metric-value">0.92</div>
                  <div className="metric-label">F1 Score</div>
                </div>
                <div className="metric">
                  <div className="metric-value">0.89</div>
                  <div className="metric-label">ROC AUC</div>
                </div>
              </div>
              <button className="btn btn-primary">Запустить прогноз</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default AnalysisPage