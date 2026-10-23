import { create } from 'zustand'

const DEFAULT_MAP_CENTER = [55.7558, 37.6173]
const DEFAULT_MAP_ZOOM = 10
const MIN_MAP_ZOOM = 2
const MAX_MAP_ZOOM = 19

function isValidCenter(center) {
  return (
    Array.isArray(center) &&
    center.length >= 2 &&
    typeof center[0] === 'number' &&
    typeof center[1] === 'number' &&
    Number.isFinite(center[0]) &&
    Number.isFinite(center[1]) &&
    center[0] >= -90 &&
    center[0] <= 90 &&
    center[1] >= -180 &&
    center[1] <= 180
  )
}

function normalizeZoom(zoom) {
  const value = Number(zoom)

  if (!Number.isFinite(value)) {
    return DEFAULT_MAP_ZOOM
  }

  return Math.min(
    MAX_MAP_ZOOM,
    Math.max(MIN_MAP_ZOOM, Math.round(value))
  )
}

export const useMapStore = create((set) => ({
  selectedArea: null,
  layers: [],
  mapCenter: [...DEFAULT_MAP_CENTER],
  mapZoom: DEFAULT_MAP_ZOOM,

  // Выбрать участок или сбросить выбор значением null.
  setSelectedArea: (area) => {
    set({ selectedArea: area ?? null })
  },

  // Добавить слой, не создавая дубликат с тем же id.
  addLayer: (layer) => {
    if (!layer || layer.id == null) {
      return
    }

    set((state) => {
      const exists = state.layers.some(
        (item) => item.id === layer.id
      )

      if (exists) {
        return {
          layers: state.layers.map((item) =>
            item.id === layer.id ? { ...item, ...layer } : item
          ),
        }
      }

      return {
        layers: [...state.layers, layer],
      }
    })
  },

  // Удалить слой по идентификатору.
  removeLayer: (layerId) => {
    set((state) => ({
      layers: state.layers.filter(
        (layer) => layer.id !== layerId
      ),
    }))
  },

  // Заменить список слоёв.
  setLayers: (layers) => {
    set({
      layers: Array.isArray(layers)
        ? layers.filter(
            (layer) => layer && layer.id != null
          )
        : [],
    })
  },

  // Очистить список слоёв.
  clearLayers: () => set({ layers: [] }),

  // Установить центр карты в формате [широта, долгота].
  setMapCenter: (center) => {
    if (!isValidCenter(center)) {
      return
    }

    set({
      mapCenter: [center[0], center[1]],
    })
  },

  // Установить допустимый масштаб карты.
  setMapZoom: (zoom) => {
    set({
      mapZoom: normalizeZoom(zoom),
    })
  },

  // Сбросить выбор и вернуть начальный вид карты.
  resetMap: () => {
    set({
      selectedArea: null,
      mapCenter: [...DEFAULT_MAP_CENTER],
      mapZoom: DEFAULT_MAP_ZOOM,
    })
  },
}))

export {
  DEFAULT_MAP_CENTER,
  DEFAULT_MAP_ZOOM,
  MIN_MAP_ZOOM,
  MAX_MAP_ZOOM,
}
