import { create } from 'zustand'

export const useMapStore = create((set) => ({
  selectedArea: null,
  layers: [],
  mapCenter: [55.7558, 37.6173],
  mapZoom: 10,

  setSelectedArea: (area) => set({ selectedArea: area }),

  addLayer: (layer) => set((state) => ({
    layers: [...state.layers, layer]
  })),

  removeLayer: (layerId) => set((state) => ({
    layers: state.layers.filter(l => l.id !== layerId)
  })),

  setMapCenter: (center) => set({ mapCenter: center }),

  setMapZoom: (zoom) => set({ mapZoom: zoom })
}))