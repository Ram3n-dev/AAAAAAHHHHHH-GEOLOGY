import { FileText, Download, Calendar } from 'lucide-react'
import '../styles/PlaceholderPage.css'

function ReportsPage() {
  const reports = [
    { name: 'Отчёт по участку "Северный-1"', date: '2024-03-20', size: '2.4 MB' },
    { name: 'Квартальный отчёт Q1 2024', date: '2024-03-31', size: '5.1 MB' },
    { name: 'Анализ рентабельности', date: '2024-03-15', size: '1.8 MB' },
  ]

  return (
    <div className="placeholder-page">
      <div className="page-header">
        <h1>Отчёты</h1>
        <p>Генерация и управление отчётами</p>
      </div>

      <div className="reports-list">
        {reports.map((report, index) => (
          <div key={index} className="report-card">
            <FileText size={24} className="report-icon" />
            <div className="report-info">
              <h3>{report.name}</h3>
              <div className="report-meta">
                <span><Calendar size={14} /> {report.date}</span>
                <span>{report.size}</span>
              </div>
            </div>
            <button className="btn btn-secondary">
              <Download size={16} />
              Скачать
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ReportsPage