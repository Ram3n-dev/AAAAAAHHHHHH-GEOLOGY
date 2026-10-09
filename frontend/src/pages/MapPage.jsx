import { useState } from 'react'
import { MapContainer, TileLayer, Polygon, Marker, Popup, useMap } from 'react-leaflet'
import { useMapStore } from '../stores/mapStore'
import { mockAreas, mockDataPoints } from '../mock/areas'
import { Layers, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react'
import 'leaflet/dist/leaflet.css'
import '../styles/MapPage.css'

function MapControls() {
  const map = useMap()
  const { setMapZoom, mapZoom } = useMapStore()

  const handleZoomIn = () => {
    map.zoomIn()
    setMapZoom(mapZoom + 1)
  }

  const handleZoomOut = () => {
    map.zoomOut()
    setMapZoom(mapZoom - 1)
  }

  const handleFitBounds = () => {
    map.fitBounds([[55.6, 37.3], [55.9, 38.0]])
  }

  return (
    <div className="map-controls">
      <button className="control-btn" onClick={handleZoomIn}><ZoomIn size={20} /></button>
      <button className="control-btn" onClick={handleZoomOut}><ZoomOut size={20} /></button>
      <button className="control-btn" onClick={handleFitBounds}><Maximize2 size={20} /></button>
      <button className="control-btn"><Layers size={20} /></button>
    </div>
  )
}

function MapPage() {
  const { selectedArea, setSelectedArea, mapCenter, mapZoom } = useMapStore()
  const [showDataPoints, setShowDataPoints] = useState(true)

  const getAreaColor = (priority) => {
    switch (priority) {
      case 'high': return '#ef4444'
      case 'medium': return '#f59e0b'
      case 'low': return '#10b981'
      default: return '#667eea'
    }
  }

  return (
    <div className="map-page">
      <div className="map-sidebar">
        <div className="sidebar-section">
          <h3>Участки</h3>
          <div className="areas-list">
            {mockAreas.map((area) => (
              <div
                key={area.id}
                className={`area-card ${selectedArea?.id === area.id ? 'active' : ''}`}
                onClick={() => setSelectedArea(area)}
              >
                <div className="area-header">
                  <div className="area-name">{area.name}</div>
                  <div className="area-priority" style={{ background: getAreaColor(area.priority) }}>
                    {area.priority === 'high' ? 'Высокий' :
                     area.priority === 'medium' ? 'Средний' : 'Низкий'}
                  </div>
                </div>
                <div className="area-details">
                  <div className="area-detail"><span>Минерал:</span><span>{area.mineralType}</span></div>
                  <div className="area-detail"><span>Запасы:</span><span>{area.estimatedReserves}</span></div>
                  <div className="area-detail"><span>Этап:</span><span>{area.explorationStage}</span></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="sidebar-section">
          <h3>Слои</h3>
          <div className="layers-list">
            <label className="layer-item">
              <input type="checkbox" checked={showDataPoints} onChange={(e) => setShowDataPoints(e.target.checked)} />
              <span>Точки данных</span>
            </label>
            <label className="layer-item">
              <input type="checkbox" defaultChecked />
              <span>Геологические границы</span>
            </label>
            <label className="layer-item">
              <input type="checkbox" />
              <span>Сейсмические данные</span>
            </label>
          </div>
        </div>
      </div>

      <div className="map-container">
        <MapContainer center={mapCenter} zoom={mapZoom} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          />

          {mockAreas.map((area) => (
            <Polygon
              key={area.id}
              positions={area.coordinates}
              pathOptions={{
                color: getAreaColor(area.priority),
                fillColor: getAreaColor(area.priority),
                fillOpacity: selectedArea?.id === area.id ? 0.4 : 0.2,
                weight: selectedArea?.id === area.id ? 3 : 2,
              }}
              eventHandlers={{ click: () => setSelectedArea(area) }}
            >
              <Popup>
                <div className="popup-content">
                  <h4>{area.name}</h4>
                  <p>Минерал: {area.mineralType}</p>
                  <p>Запасы: {area.estimatedReserves}</p>
                </div>
              </Popup>
            </Polygon>
          ))}

          {showDataPoints && mockDataPoints.map((point) => (
            <Marker key={point.id} position={point.coordinates}>
              <Popup>
                <div className="popup-content">
                  <h4>{point.type === 'borehole' ? 'Скважина' : 'Проба'}</h4>
                  {point.type === 'borehole' && (
                    <>
                      <p>Глубина: {point.depth} м</p>
                      <p>Образцов: {point.samples}</p>
                    </>
                  )}
                  {point.type === 'sample' && (
                    <>
                      <p>Минерал: {point.mineral}</p>
                      <p>Концентрация: {point.concentration} г/т</p>
                    </>
                  )}
                </div>
              </Popup>
            </Marker>
          ))}

          <MapControls />
        </MapContainer>
      </div>
    </div>
  )
}

export default MapPage