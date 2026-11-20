import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  ImageOverlay,
  useMap,
  useMapEvents,
} from 'react-leaflet'
import L from 'leaflet'
import {
  Layers,
  ZoomIn,
  ZoomOut,
  Maximize2,
  MapPinned,
  CircleDot,
  Activity,
  Check,
  X,
} from 'lucide-react'
import { useMapStore } from '../stores/mapStore'
import {
  getCell,
  getDeposits,
  getScoresMapPngUrl,
} from '../services/api'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import 'leaflet/dist/leaflet.css'
import '../styles/MapPage.css'

// Иконка маркера — отдельным L.Icon, а не через Icon.Default:
// дефолтная иконка Leaflet дописывает свой imagePath к заданному URL,
// и под Vite получается двойной путь вида
// /node_modules/leaflet/dist/images//node_modules/leaflet/dist/images/marker-icon.png.
// У обычного L.Icon такого дописывания нет.
const depositIcon = new L.Icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

const DEFAULT_BOUNDS_PADDING = [40, 40]
const MAX_FIT_ZOOM = 12

// Границы растра scores-map.png: bbox центров ячеек площади PoC (Р-5).
// Сетка в метрах EPSG:32646, поэтому растр — диагностическая карта,
// а не геопривязанный GeoTIFF.
const SCORES_BOUNDS = [
  [58.5, 92.3],
  [60.6, 95.0],
]

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

function MapViewport({ allPositions }) {
  const map = useMap()

  useEffect(() => {
    if (!allPositions || allPositions.length === 0) return

    map.fitBounds(allPositions, {
      padding: DEFAULT_BOUNDS_PADDING,
      maxZoom: MAX_FIT_ZOOM,
    })
  }, [map, allPositions])

  return null
}

// Клик по карточке месторождения в сайдбаре: долететь до маркера.
function MapFlyTo({ target }) {
  const map = useMap()

  useEffect(() => {
    if (!target || !isValidPosition([target.latitude, target.longitude])) {
      return
    }

    map.flyTo([target.latitude, target.longitude], Math.max(map.getZoom(), 9))
  }, [map, target])

  return null
}

// Клик по карте: запрашиваем оценку ячейки у бэкенда.
function MapClickHandler({ onPickCell }) {
  useMapEvents({
    click(event) {
      onPickCell(event.latlng.lat, event.latlng.lng)
    },
  })

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

// Попап кликнутой ячейки: оценка, вклады, месторождение или нет.
function CellPopupContent({ cell }) {
  if (!cell) return null

  if (cell.loading) {
    return (
      <div className="popup-content">
        <h4>Ячейка {cell.latitude.toFixed(4)}, {cell.longitude.toFixed(4)}</h4>
        <p>Загрузка оценки…</p>
      </div>
    )
  }

  if (cell.error) {
    return (
      <div className="popup-content">
        <h4>Ячейка {cell.latitude.toFixed(4)}, {cell.longitude.toFixed(4)}</h4>
        <p>Не удалось получить оценку: {cell.error}</p>
      </div>
    )
  }

  const data = cell.data
  if (!data) return null

  const topContributions = [...(data.contributions || [])]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .slice(0, 3)

  return (
    <div className="popup-content cell-popup">
      <h4>{data.deposit_name || 'Ячейка без месторождения'}</h4>
      <p>
        <strong>Оценка:</strong> {data.score.toFixed(3)}
        <span className="cell-popup-hint"> (перцентиль 0–1, не вероятность)</span>
      </p>
      <p>
        <strong>Сырая сумма WoE:</strong> {data.score_raw.toFixed(3)}
      </p>
      <p>
        <strong>Фолд:</strong> {data.fold_id}
      </p>

      {topContributions.length > 0 && (
        <>
          <p className="cell-popup-subheading">Главные вклады:</p>
          {topContributions.map((item) => (
            <p key={item.feature}>
              {item.feature}: {item.contribution > 0 ? '+' : ''}
              {item.contribution.toFixed(2)}
            </p>
          ))}
        </>
      )}
    </div>
  )
}

function MapPage() {
  const {
    selectedArea,
    setSelectedArea,
    mapCenter,
    mapZoom,
  } = useMapStore()

  const [deposits, setDeposits] = useState([])
  const [depositsStatus, setDepositsStatus] = useState('loading')
  const [depositsError, setDepositsError] = useState('')
  const [showDeposits, setShowDeposits] = useState(true)
  const [showScores, setShowScores] = useState(true)
  const [showSeismicData, setShowSeismicData] = useState(false)
  const [baseLayer, setBaseLayer] = useState('standard')
  const [clickedCell, setClickedCell] = useState(null)

  const loadDeposits = useCallback(async () => {
    setDepositsStatus('loading')
    setDepositsError('')
    try {
      const data = await getDeposits()
      setDeposits(Array.isArray(data) ? data : [])
      setDepositsStatus('ready')
    } catch (error) {
      setDepositsStatus('error')
      setDepositsError(
        error?.response?.status
          ? `Бэкенд ответил ${error.response.status}`
          : 'Бэкенд недоступен. Проверьте, что API запущен на :8000.'
      )
    }
  }, [])

  useEffect(() => {
    loadDeposits()
  }, [loadDeposits])

  const depositPositions = useMemo(
    () =>
      deposits
        .map((deposit) => [deposit.latitude, deposit.longitude])
        .filter((position) => isValidPosition(position)),
    [deposits]
  )

  const allPositions = useMemo(
    () => [...depositPositions],
    [depositPositions]
  )

  // Клик по карте или по маркеру: одна и та же оценка ячейки.
  const handlePickCell = useCallback(async (latitude, longitude) => {
    setClickedCell({ latitude, longitude, loading: true, data: null, error: '' })
    try {
      const data = await getCell(latitude, longitude)
      setClickedCell({ latitude, longitude, loading: false, data, error: '' })
    } catch (error) {
      setClickedCell({
        latitude,
        longitude,
        loading: false,
        data: null,
        error:
          error?.response?.status === 404
            ? 'Точка вне площади проекта.'
            : 'Бэкенд недоступен.',
      })
    }
  }, [])

  const handleToggleBaseLayer = () => {
    setBaseLayer((current) =>
      current === 'standard' ? 'humanitarian' : 'standard'
    )
  }

  const handleSelectDeposit = (deposit) => {
    const isSelected = selectedArea?.name === deposit.name
    setSelectedArea(isSelected ? null : deposit)
    if (!isSelected) {
      handlePickCell(deposit.latitude, deposit.longitude)
    }
  }

  const handleClearSelection = () => {
    setSelectedArea(null)
    setClickedCell(null)
  }

  const enabledLayersCount = [
    showDeposits,
    showScores,
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
            <p>Енисейский кряж — перспективность золота</p>
          </div>
        </div>

        <div className="map-sidebar-content">
          <section className="sidebar-section">
            <div className="section-heading">
              <div>
                <h3>Месторождения</h3>
                <p>Выберите месторождение для приближения</p>
              </div>
              <span className="section-count">{deposits.length}</span>
            </div>

            {depositsStatus === 'loading' && (
              <div className="map-empty-state">
                <MapPinned size={22} />
                <p>Загрузка месторождений из GeoLens API…</p>
              </div>
            )}

            {depositsStatus === 'error' && (
              <div className="map-empty-state">
                <MapPinned size={22} />
                <p>Месторождения не загрузились: {depositsError}</p>
                <button
                  type="button"
                  className="clear-selection-btn"
                  onClick={loadDeposits}
                >
                  Повторить
                </button>
              </div>
            )}

            {depositsStatus === 'ready' && (
              <div className="areas-list">
                {deposits.length === 0 ? (
                  <div className="map-empty-state">
                    <MapPinned size={22} />
                    <p>Бэкенд не вернул месторождений.</p>
                  </div>
                ) : (
                  deposits.map((deposit) => {
                    const isSelected = selectedArea?.name === deposit.name

                    return (
                      <button
                        type="button"
                        key={deposit.name}
                        className={`area-card ${
                          isSelected ? 'active' : ''
                        }`}
                        onClick={() => handleSelectDeposit(deposit)}
                        aria-pressed={isSelected}
                      >
                        <span
                          className="area-color-indicator"
                          style={{ backgroundColor: '#5eead4' }}
                        />

                        <span className="area-card-content">
                          <span className="area-header">
                            <span className="area-name">{deposit.name}</span>
                          </span>

                          <span className="area-details">
                            <span className="area-detail">
                              <span>Фолд</span>
                              <strong>{deposit.fold_id}</strong>
                            </span>
                            <span className="area-detail">
                              <span>Координаты</span>
                              <strong>
                                {deposit.latitude.toFixed(3)},{' '}
                                {deposit.longitude.toFixed(3)}
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
            )}

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
                checked={showScores}
                onChange={setShowScores}
                icon={Layers}
                title="Карта перспективности"
                description="Растр оценок с бэкенда (scores.png)"
                color="#5eead4"
              />

              <LayerToggle
                checked={showDeposits}
                onChange={setShowDeposits}
                icon={MapPinned}
                title="Месторождения"
                description="11 известных месторождений"
                count={deposits.length}
                color="#60a5fa"
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
              <div className="legend-item legend-gradient-row">
                <span className="legend-gradient" aria-hidden="true" />
                <span>Перцентиль оценки: 0 — низкая, 1 — высокая</span>
              </div>
              <div className="legend-gradient-scale" aria-hidden="true">
                <span>0</span>
                <span>0,5</span>
                <span>1</span>
              </div>
              <div className="legend-item">
                <span className="legend-point legend-deposit" />
                <span>Месторождение</span>
              </div>
              <div className="legend-note">
                Оценка — перцентиль сырой суммы WoE среди всех ячеек,
                а не вероятность месторождения.
              </div>
            </div>
          </section>
        </div>

        <div className="map-sidebar-footer">
          <span className="map-status-dot" />
          <span>Данные: GeoLens API</span>
          <span className="map-footer-count">
            {deposits.length} мест.
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
              {deposits.length} месторождений
            </span>
            <span>
              <CircleDot size={14} />
              Клик по карте — оценка ячейки
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

          <MapViewport allPositions={allPositions} />

          <MapFlyTo target={selectedArea} />

          <MapClickHandler onPickCell={handlePickCell} />

          {showScores && (
            <ImageOverlay
              url={getScoresMapPngUrl()}
              bounds={SCORES_BOUNDS}
              opacity={0.6}
              zIndex={10}
            />
          )}

          {showDeposits &&
            deposits.map((deposit) => (
              <Marker
                key={deposit.name}
                icon={depositIcon}
                position={[deposit.latitude, deposit.longitude]}
                eventHandlers={{
                  click: () =>
                    handlePickCell(deposit.latitude, deposit.longitude),
                }}
              />
            ))}

          {clickedCell && (
            <Popup
              position={[clickedCell.latitude, clickedCell.longitude]}
              eventHandlers={{
                remove: () => setClickedCell(null),
              }}
            >
              <CellPopupContent cell={clickedCell} />
            </Popup>
          )}

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
