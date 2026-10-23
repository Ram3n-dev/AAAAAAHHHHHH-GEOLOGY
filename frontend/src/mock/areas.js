/**
 * Демонстрационные данные GeoLens.
 *
 * ВНИМАНИЕ:
 * Координаты, запасы и характеристики ниже являются тестовыми.
 * Они не должны использоваться как реальные геологические сведения.
 *
 * Координаты для React Leaflet задаются в формате [широта, долгота].
 */

export const mockAreas = [
  {
    id: 1,
    name: 'Участок "Северный-1"',
    coordinates: [
      [55.8, 37.5],
      [55.8, 37.7],
      [55.9, 37.7],
      [55.9, 37.5],
    ],
    status: 'active',
    priority: 'high',
    mineralType: 'Золото',
    estimatedReserves: '15.2 т',
    explorationStage: 'Детальная разведка',
    description:
      'Демонстрационный участок для проверки интерфейса геологической карты.',
    updatedAt: '2024-03-20',
    dataSource: 'mock',
  },
  {
    id: 2,
    name: 'Участок "Восточный"',
    coordinates: [
      [55.7, 37.8],
      [55.7, 38.0],
      [55.8, 38.0],
      [55.8, 37.8],
    ],
    status: 'active',
    priority: 'medium',
    mineralType: 'Медь',
    estimatedReserves: '120 тыс. т',
    explorationStage: 'Предварительная разведка',
    description:
      'Демонстрационный участок для проверки фильтров и выделения объектов.',
    updatedAt: '2024-02-28',
    dataSource: 'mock',
  },
  {
    id: 3,
    name: 'Участок "Западный"',
    coordinates: [
      [55.6, 37.3],
      [55.6, 37.5],
      [55.7, 37.5],
      [55.7, 37.3],
    ],
    status: 'planning',
    priority: 'low',
    mineralType: 'Железо',
    estimatedReserves: '5.8 млн т',
    explorationStage: 'Поисковые работы',
    description:
      'Демонстрационный участок на стадии планирования исследований.',
    updatedAt: '2024-01-15',
    dataSource: 'mock',
  },
]

export const mockDataPoints = [
  {
    id: 1,
    areaId: 1,
    type: 'borehole',
    name: 'Скважина BH-001',
    coordinates: [55.85, 37.6],
    depth: 450,
    samples: 24,
    date: '2024-03-15',
    dataSource: 'mock',
  },
  {
    id: 2,
    areaId: 1,
    type: 'sample',
    name: 'Проба SMP-001',
    coordinates: [55.83, 37.62],
    mineral: 'Au',
    concentration: 2.5,
    date: '2024-03-20',
    dataSource: 'mock',
  },
  {
    id: 3,
    areaId: 2,
    type: 'borehole',
    name: 'Скважина BH-002',
    coordinates: [55.75, 37.9],
    depth: 320,
    samples: 18,
    date: '2024-02-28',
    dataSource: 'mock',
  },
]

/**
 * Допустимые значения статусов и приоритетов.
 * Их можно использовать в фильтрах и формах.
 */

export const areaStatuses = [
  { value: 'active', label: 'Активный' },
  { value: 'planning', label: 'Планирование' },
]

export const areaPriorities = [
  { value: 'high', label: 'Высокий' },
  { value: 'medium', label: 'Средний' },
  { value: 'low', label: 'Низкий' },
]

export const dataPointTypes = [
  { value: 'borehole', label: 'Скважина' },
  { value: 'sample', label: 'Проба' },
]

/**
 * Возвращает точки, принадлежащие указанному участку.
 */
export function getDataPointsByArea(areaId) {
  return mockDataPoints.filter(
    (point) => point.areaId === areaId
  )
}

/**
 * Возвращает список минералов для фильтра.
 */
export function getAvailableMinerals() {
  return [...new Set(
    mockAreas
      .map((area) => area.mineralType)
      .filter(Boolean)
  )].sort((a, b) => a.localeCompare(b, 'ru'))
}

/**
 * Проверяет координату в формате [широта, долгота].
 */
export function isValidCoordinates(coordinates) {
  return (
    Array.isArray(coordinates) &&
    coordinates.length >= 2 &&
    typeof coordinates[0] === 'number' &&
    typeof coordinates[1] === 'number' &&
    Number.isFinite(coordinates[0]) &&
    Number.isFinite(coordinates[1]) &&
    coordinates[0] >= -90 &&
    coordinates[0] <= 90 &&
    coordinates[1] >= -180 &&
    coordinates[1] <= 180
  )
}
