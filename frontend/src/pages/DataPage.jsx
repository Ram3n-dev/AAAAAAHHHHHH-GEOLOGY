import { useState } from 'react'
import { Upload, Download, Filter, Search, FileText, Database } from 'lucide-react'
import '../styles/DataPage.css'

function DataPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterType, setFilterType] = useState('all')

  const mockData = [
    { id: 1, name: 'Пробы участка "Северный-1"', type: 'samples', count: 124, date: '2024-03-20', size: '2.4 MB' },
    { id: 2, name: 'Данные бурения Q1 2024', type: 'borehole', count: 48, date: '2024-03-15', size: '5.1 MB' },
    { id: 3, name: 'Геофизические измерения', type: 'geophysical', count: 256, date: '2024-03-10', size: '12.8 MB' },
    { id: 4, name: 'Лабораторные анализы', type: 'lab', count: 89, date: '2024-03-05', size: '1.8 MB' },
  ]

  const filteredData = mockData.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFilter = filterType === 'all' || item.type === filterType
    return matchesSearch && matchesFilter
  })

  return (
    <div className="data-page">
      <div className="page-header">
        <h1>Данные</h1>
        <p>Управление геологическими данными и пробами</p>
      </div>

      <div className="data-toolbar">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Поиск данных..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <select className="filter-select" value={filterType} onChange={(e) => setFilterType(e.target.value)}>
            <option value="all">Все типы</option>
            <option value="samples">Пробы</option>
            <option value="borehole">Бурение</option>
            <option value="geophysical">Геофизика</option>
            <option value="lab">Лаборатория</option>
          </select>
        </div>

        <button className="btn btn-primary">
          <Upload size={18} />
          Загрузить данные
        </button>
      </div>

      <div className="data-stats">
        <div className="stat-box">
          <Database size={24} />
          <div className="stat-info">
            <div className="stat-value">517</div>
            <div className="stat-label">Всего записей</div>
          </div>
        </div>
        <div className="stat-box">
          <FileText size={24} />
          <div className="stat-info">
            <div className="stat-value">22.1 MB</div>
            <div className="stat-label">Общий объём</div>
          </div>
        </div>
      </div>

      <div className="data-table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Название</th>
              <th>Тип</th>
              <th>Записей</th>
              <th>Дата</th>
              <th>Размер</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {filteredData.map((item) => (
              <tr key={item.id}>
                <td>
                  <div className="data-name">
                    <FileText size={16} />
                    {item.name}
                  </div>
                </td>
                <td>
                  <span className={`type-badge type-${item.type}`}>
                    {item.type === 'samples' ? 'Пробы' :
                     item.type === 'borehole' ? 'Бурение' :
                     item.type === 'geophysical' ? 'Геофизика' : 'Лаборатория'}
                  </span>
                </td>
                <td>{item.count}</td>
                <td>{item.date}</td>
                <td>{item.size}</td>
                <td>
                  <div className="action-buttons">
                    <button className="icon-btn-sm" title="Скачать"><Download size={16} /></button>
                    <button className="icon-btn-sm" title="Фильтр"><Filter size={16} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default DataPage