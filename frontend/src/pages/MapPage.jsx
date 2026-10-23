
import { useEffect, useMemo, useState } from 'react'
import {
  MapContainer,
  TileLayer,
  Polygon,
  Marker,
  Popup,
  useMap,
} from 'react-leaflet'
import {
  Layers,
  ZoomIn,
  ZoomOut,
  Maximize2,
  MapPinned,
  CircleDot,
  Drill,
  FlaskConical,
  Activity,
  Check,
  X,
} from 'lucide-react'
import { useMapStore } from '../stores/mapStore'
import { mockAreas, mockDataPoints } from '../mock/areas'
import 'leaflet/dist/leaflet.css'
import '../styles/MapPage.css'

const DEFAULT_BOUNDS_PADDING = [40, 40]
const MAX_FIT_ZOOM = 12

function isValidPosition(position) {
  return (
    Array.isArray(position) &&
    position.length >= 2 &&
    typeof position[0] === 'number' &&
    typeof position[1] === 'number' &&
    Number.isFinite(position[0]) &&
    Number.isFinite(position[1]) &&
    position[0] >= -90 &&
    position[0] <= 90 &&
    position[1] >= -180 &&
    position[1] <= 180
  )
}

function collectPositions(value, result = []) {
  if (!Array.isArray(value)) return result

  if (isValidPosition(value)) {
    result.push([value[0], value[1]])
    return result
  }

  value.forEach((item) => collectPositions(item, result))
  return result
}

function getAreaColor(priority) {
  switch (priority) {
    case 'high':
      return '#f87171'
    case 'medium':
      return '#fbbf24'
    case 'low':
      return '#34d399'
    default:
      return '#5eead4'
  }
}

function getPriorityLabel(priority) {
  switch (priority) {
    case 'high':
      return 'Высокий'
    case 'medium':
      return 'Средний'
    case 'low':
      return 'Низкий'
    default:
      return 'Не указан'
  }
}

function getAreaBounds(area) {
  const positions = collectPositions(area?.coordinates)
  return positions.length > 0 ? positions : null
}

function getPointTypeLabel(type) {
  if (type === 'borehole') return 'Скважина'
  if (type === 'sample') return 'Проба'
  return 'Точка данных'
}

function MapViewport({ selectedArea, allPositions }) {
  const map = useMap()

  useEffect(() => {
    const selectedPositions = selectedArea
      ? getAreaBounds(selectedArea)
      : null

    const positions =
      selectedPositions?.length > 0 ? selectedPositions : allPositions

    if (!positions || positions.length === 0) return

    map.fitBounds(positions, {
      padding: DEFAULT_BOUNDS_PADDING,
      maxZoom: MAX_FIT_ZOOM,
    })
  }, [map, selectedArea, allPositions])

  return null
}

function MapControls({ allPositions, baseLayer, onToggleBaseLayer }) {
  const map = useMap()
  const { setMapZoom } = useMapStore()

  const handleZoomIn = () => {
    map.zoomIn()
    setMapZoom(map.getZoom() + 1)
  }

  const handleZoomOut = () => {
    map.zoomOut()
    setMapZoom(Math.max(0, map.getZoom() - 1))
  }

  const handleFitBounds = () => {
    if (allPositions.length > 0) {
      map.fitBounds(allPositions, {
        padding: DEFAULT_BOUNDS_PADDING,
        maxZoom: MAX_FIT_ZOOM,
      })
    }
  }

  return (
    <div className="map-controls">
      <button
        type="button"
        className="control-btn"
        onClick={handleZoomIn}
        title="Приблизить"
        aria-label="Приблизить карту"
      >
        <ZoomIn size={19} />
      </button>

      <button
        type="button"
        className="control-btn"
        onClick={handleZoomOut}
        title="Отдалить"
        aria-label="Отдалить карту"
      >
        <ZoomOut size={19} />
      </button>

      <button
        type="button"
        className="control-btn"
        onClick={handleFitBounds}
        title="Показать все объекты"
        aria-label="Показать все объекты"
      >
        <Maximize2 size={18} />
      </button>

      <div className="map-controls-divider" />

      <button
        type="button"
        className={`control-btn ${
          baseLayer === 'humanitarian' ? 'active' : ''
        }`}
        onClick={onToggleBaseLayer}
        title="Изменить подложку карты"
        aria-label="Изменить подложку карты"
      >
        <Layers size={19} />
      </button>
    </div>
  )
}

function LayerToggle({
  checked,
  onChange,
  icon: Icon,
  title,
  description,
  count,
  color,
}) {
  return (
    <label className={`map-layer ${checked ? 'is-enabled' : ''}`}>
      <span
        className="layer-symbol"
        style={{ '--layer-color': color }}
        aria-hidden="true"
      >
        <Icon size={17} />
      </span>

      <span className="layer-copy">
        <span className="layer-title">{title}</span>
        <span className="layer-description">{description}</span>
      </span>

      {Number.isFinite(count) && (
        <span className="layer-count">{count}</span>
      )}

      <input
        className="layer-checkbox"
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        aria-label={title}
      />

      <span className="layer-switch" aria-hidden="true">
        <span />
      </span>
    </label>
  )
}

function MapPage() {
  const {
    selectedArea,
    setSelectedArea,
    mapCenter,
    mapZoom,
  } = useMapStore()

  const [showDataPoints, setShowDataPoints] = useState(true)
  const [showGeologicalBoundaries, setShowGeologicalBoundaries] =
    useState(true)
  const [showSeismicData, setShowSeismicData] = useState(false)
  const [baseLayer, setBaseLayer] = useState('standard')

  const validAreas = useMemo(
    () =>
      mockAreas.filter(
        (area) => (getAreaBounds(area)?.length ?? 0) >= 3
      ),
    []
  )

  const validDataPoints = useMemo(
    () =>
      mockDataPoints.filter((point) =>
        isValidPosition(point.coordinates)
      ),
    []
  )

  const pointCounts = useMemo(
    () => ({
      boreholes: validDataPoints.filter(
        (point) => point.type === 'borehole'
      ).length,
      samples: validDataPoints.filter(
        (point) => point.type === 'sample'
      ).length,
      other: validDataPoints.filter(
        (point) =>
          point.type !== 'borehole' && point.type !== 'sample'
      ).length,
    }),
    [validDataPoints]
  )

  const allPositions = useMemo(() => {
    const areaPositions = validAreas.flatMap((area) =>
      collectPositions(area.coordinates)
    )
    const pointPositions = validDataPoints.flatMap((point) =>
      collectPositions(point.coordinates)
    )

    return [...areaPositions, ...pointPositions]
  }, [validAreas, validDataPoints])

  const handleToggleBaseLayer = () => {
    setBaseLayer((current) =>
      current === 'standard' ? 'humanitarian' : 'standard'
    )
  }

  const handleSelectArea = (area) => {
    setSelectedArea(
      selectedArea?.id === area.id ? null : area
    )
  }

  const handleClearSelection = () => {
    setSelectedArea(null)
  }

  const enabledLayersCount = [
    showDataPoints,
    showGeologicalBoundaries,
    showSeismicData,
  ].filter(Boolean).length

  return (
    <div className="map-page">
      <aside className="map-sidebar">
        <div className="map-sidebar-heading">
          <div className="map-heading-icon">
            <MapPinned size={21} />
          </div>
          <div>
            <h2>Геокарта</h2>
            <p>Пространственные данные проекта</p>
          </div>
        </div>

        <div className="map-sidebar-content">
          <section className="sidebar-section">
            <div className="section-heading">
              <div>
                <h3>Участки</h3>
                <p>Выберите участок для приближения</p>
              </div>
              <span className="section-count">{validAreas.length}</span>
            </div>

            <div className="areas-list">
              {validAreas.length === 0 ? (
                <div className="map-empty-state">
                  <MapPinned size={22} />
                  <p>Нет участков с корректными координатами.</p>
                </div>
              ) : (
                validAreas.map((area) => {
                  const isSelected = selectedArea?.id === area.id

                  return (
                    <button
                      type="button"
                      key={area.id}
                      className={`area-card ${
                        isSelected ? 'active' : ''
                      }`}
                      onClick={() => handleSelectArea(area)}
                      aria-pressed={isSelected}
                    >
                      <span
                        className="area-color-indicator"
                        style={{
                          backgroundColor: getAreaColor(area.priority),
                        }}
                      />

                      <span className="area-card-content">
                        <span className="area-header">
                          <span className="area-name">{area.name}</span>
                          <span
                            className={`area-priority priority-${area.priority || 'default'}`}
                          >
                            {getPriorityLabel(area.priority)}
                          </span>
                        </span>

                        <span className="area-details">
                          <span className="area-detail">
                            <span>Минерал</span>
                            <strong>{area.mineralType || 'Не указан'}</strong>
                          </span>
                          <span className="area-detail">
                            <span>Запасы</span>
                            <strong>
                              {area.estimatedReserves ?? 'Нет данных'}
                            </strong>
                          </span>
                          <span className="area-detail">
                            <span>Этап</span>
                            <strong>
                              {area.explorationStage || 'Не указан'}
                            </strong>
                          </span>
                        </span>
                      </span>

                      {isSelected && (
                        <span className="area-selected-icon">
                          <Check size={15} />
                        </span>
                      )}
                    </button>
                  )
                })
              )}
            </div>

            {selectedArea && (
              <button
                type="button"
                className="clear-selection-btn"
                onClick={handleClearSelection}
              >
                <X size={15} />
                Снять выделение
              </button>
            )}
          </section>

          <section className="sidebar-section layers-section">
            <div className="section-heading">
              <div>
                <h3>Слои карты</h3>
                <p>Управление отображением</p>
              </div>
              <span className="section-count">
                {enabledLayersCount}/3
              </span>
            </div>

            <div className="layers-list">
              <LayerToggle
                checked={showGeologicalBoundaries}
                onChange={setShowGeologicalBoundaries}
                icon={Layers}
                title="Границы участков"
                description="Полигоны и контуры"
                count={validAreas.length}
                color="#5eead4"
              />

              <LayerToggle
                checked={showDataPoints}
                onChange={setShowDataPoints}
                icon={Drill}
                title="Скважины"
                description="Точки бурения"
                count={pointCounts.boreholes}
                color="#60a5fa"
              />

              <LayerToggle
                checked={showDataPoints}
                onChange={setShowDataPoints}
                icon={FlaskConical}
                title="Пробы и измерения"
                description="Точки отбора проб"
                count={pointCounts.samples + pointCounts.other}
                color="#c084fc"
              />

              <LayerToggle
                checked={showSeismicData}
                onChange={setShowSeismicData}
                icon={Activity}
                title="Сейсмические данные"
                description="Отдельный слой не подключён"
                color="#fbbf24"
              />
            </div>

            {showSeismicData && (
              <div className="layer-notice">
                <Activity size={16} />
                <p>
                  Сейсмический слой пока не подключён. Его переключатель
                  сохранён для будущего расширения.
                </p>
              </div>
            )}
          </section>

          <section className="sidebar-section legend-section">
            <div className="section-heading">
              <div>
                <h3>Легенда</h3>
                <p>Обозначения на карте</p>
              </div>
              <CircleDot size={18} className="legend-heading-icon" />
            </div>

            <div className="legend-list">
              <div className="legend-item">
                <span className="legend-polygon legend-high" />
                <span>Высокий приоритет</span>
              </div>
              <div className="legend-item">
                <span className="legend-polygon legend-medium" />
                <span>Средний приоритет</span>
              </div>
              <div className="legend-item">
                <span className="legend-polygon legend-low" />
                <span>Низкий приоритет</span>
              </div>
              <div className="legend-item">
                <span className="legend-point legend-borehole" />
                <span>Скважина</span>
              </div>
              <div className="legend-item">
                <span className="legend-point legend-sample" />
                <span>Проба</span>
              </div>
            </div>
          </section>
        </div>

        <div className="map-sidebar-footer">
          <span className="map-status-dot" />
          <span>Демонстрационные данные</span>
          <span className="map-footer-count">
            {validAreas.length} уч. · {validDataPoints.length} точ.
          </span>
        </div>
      </aside>

      <main className="map-container">
        <div className="map-top-overlay">
          <div className="map-live-label">
            <span className="map-status-dot" />
            <span>
              {baseLayer === 'standard'
                ? 'OpenStreetMap'
                : 'Humanitarian'}
            </span>
          </div>

          <div className="map-object-summary">
            <span>
              <MapPinned size={14} />
              {validAreas.length} участков
            </span>
            <span>
              <CircleDot size={14} />
              {showDataPoints ? validDataPoints.length : 0} точек
            </span>
          </div>
        </div>

        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          zoomControl={false}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom
        >
          {baseLayer === 'standard' ? (
            <TileLayer
              key="standard"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            />
          ) : (
            <TileLayer
              key="humanitarian"
              url="https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png"
              attribution="&copy; OpenStreetMap contributors, Tiles: HOT"
            />
          )}

          <MapViewport
            selectedArea={selectedArea}
            allPositions={allPositions}
          />

          {showGeologicalBoundaries &&
            validAreas.map((area) => (
              <Polygon
                key={area.id}
                positions={area.coordinates}
                pathOptions={{
                  color: getAreaColor(area.priority),
                  fillColor: getAreaColor(area.priority),
                  fillOpacity: selectedArea?.id === area.id ? 0.35 : 0.16,
                  weight: selectedArea?.id === area.id ? 3 : 2,
                  opacity: 0.9,
                }}
                eventHandlers={{
                  click: () => setSelectedArea(area),
                }}
              >
                <Popup>
                  <div className="popup-content">
                    <h4>{area.name}</h4>
                    <p>
                      <strong>Минерал:</strong>{' '}
                      {area.mineralType || 'Не указан'}
                    </p>
                    <p>
                      <strong>Запасы:</strong>{' '}
                      {area.estimatedReserves ?? 'Нет данных'}
                    </p>
                    <p>
                      <strong>Этап:</strong>{' '}
                      {area.explorationStage || 'Не указан'}
                    </p>
                    <p>
                      <strong>Приоритет:</strong>{' '}
                      {getPriorityLabel(area.priority)}
                    </p>
                  </div>
                </Popup>
              </Polygon>
            ))}

          {showDataPoints &&
            validDataPoints.map((point) => (
              <Marker key={point.id} position={point.coordinates}>
                <Popup>
                  <div className="popup-content">
                    <h4>{point.name || getPointTypeLabel(point.type)}</h4>
                    <p>
                      <strong>Тип:</strong>{' '}
                      {getPointTypeLabel(point.type)}
                    </p>

                    {point.type === 'borehole' && (
                      <>
                        <p>
                          <strong>Глубина:</strong>{' '}
                          {point.depth ?? 'Нет данных'} м
                        </p>
                        <p>
                          <strong>Образцов:</strong>{' '}
                          {point.samples ?? 'Нет данных'}
                        </p>
                      </>
                    )}

                    {point.type === 'sample' && (
                      <>
                        <p>
                          <strong>Минерал:</strong>{' '}
                          {point.mineral || 'Не указан'}
                        </p>
                        <p>
                          <strong>Концентрация:</strong>{' '}
                          {point.concentration ?? 'Нет данных'} г/т
                        </p>
                      </>
                    )}
                  </div>
                </Popup>
              </Marker>
            ))}

          <MapControls
            allPositions={allPositions}
            baseLayer={baseLayer}
            onToggleBaseLayer={handleToggleBaseLayer}
          />
        </MapContainer>
      </main>
    </div>
  )
}

export default MapPage
