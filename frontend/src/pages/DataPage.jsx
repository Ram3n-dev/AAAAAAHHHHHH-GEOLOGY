import { useEffect, useState } from 'react'
import { Upload, Download, Search, FileText, Database } from 'lucide-react'
import { getDeposits, getScoresCsvUrl, getStats } from '../services/api'
import '../styles/DataPage.css'

function DataPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [deposits, setDeposits] = useState([])
  const [stats, setStats] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

  const loadData = async () => {
    setStatus('loading')
    setError('')
    try {
      const [depositsData, statsData] = await Promise.all([
        getDeposits(),
        getStats(),
      ])
      setDeposits(Array.isArray(depositsData) ? depositsData : [])
      setStats(statsData)
      setStatus('ready')
    } catch (err) {
      setStatus('error')
      setError(
        err?.response?.status
          ? `Бэкенд ответил ${err.response.status}`
          : 'Бэкенд недоступен. Проверьте, что API запущен на :8000.'
      )
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const filteredData = deposits.filter((item) =>
    item.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="data-page">
      <div className="page-header">
        <h1>Данные</h1>
        <p>Месторождения и таблица признаков — из GeoLens API</p>
      </div>

      <div className="data-toolbar">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Поиск месторождения..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <a className="btn btn-primary" href={getScoresCsvUrl()} download>
          <Download size={18} />
          Скачать scores.csv
        </a>

        <button
          className="btn btn-primary"
          type="button"
          disabled
          title="Загрузка данных не подключена к бэкенду"
        >
          <Upload size={18} />
          Загрузить данные
        </button>
      </div>

      {status === 'loading' && (
        <div className="data-stats">
          <div className="stat-box">
            <Database size={24} />
            <div className="stat-info">
              <div className="stat-value">…</div>
              <div className="stat-label">Загрузка из GeoLens API…</div>
            </div>
          </div>
        </div>
      )}

      {status === 'error' && (
        <div className="data-stats">
          <div className="stat-box">
            <Database size={24} />
            <div className="stat-info">
              <div className="stat-value">Ошибка</div>
              <div className="stat-label">{error}</div>
            </div>
          </div>
          <button className="btn btn-primary" type="button" onClick={loadData}>
            Повторить
          </button>
        </div>
      )}

      {status === 'ready' && stats && (
        <div className="data-stats">
          <div className="stat-box">
            <Database size={24} />
            <div className="stat-info">
              <div className="stat-value">{stats.cells}</div>
              <div className="stat-label">Всего ячеек (1×1 км)</div>
            </div>
          </div>
          <div className="stat-box">
            <FileText size={24} />
            <div className="stat-info">
              <div className="stat-value">{stats.deposits}</div>
              <div className="stat-label">Месторождений</div>
            </div>
          </div>
          <div className="stat-box">
            <FileText size={24} />
            <div className="stat-info">
              <div className="stat-value">{stats.lithology_missing}</div>
              <div className="stat-label">Ячеек без литологии</div>
            </div>
          </div>
        </div>
      )}

      {status === 'ready' && (
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Название</th>
                <th>Фолд</th>
                <th>Широта</th>
                <th>Долгота</th>
              </tr>
            </thead>
            <tbody>
              {filteredData.length === 0 ? (
                <tr>
                  <td colSpan={4}>Ничего не найдено.</td>
                </tr>
              ) : (
                filteredData.map((item) => (
                  <tr key={item.name}>
                    <td>
                      <div className="data-name">
                        <FileText size={16} />
                        {item.name}
                      </div>
                    </td>
                    <td>{item.fold_id}</td>
                    <td>{item.latitude.toFixed(4)}</td>
                    <td>{item.longitude.toFixed(4)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default DataPage
