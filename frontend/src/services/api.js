import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// GeoLens API: бэкенд FastAPI, прокси Vite /api -> localhost:8000.
// Эндпоинты: /api/health, /api/deposits, /api/cell, /api/stats,
// /api/scores.png, /api/scores.csv (Р-5).

export async function getHealth() {
  const { data } = await api.get('/health')
  return data
}

export async function getDeposits() {
  const { data } = await api.get('/deposits')
  return data
}

export async function getCell(latitude, longitude) {
  const { data } = await api.get('/cell', {
    params: { latitude, longitude },
  })
  return data
}

export async function getStats() {
  const { data } = await api.get('/stats')
  return data
}

export function getScoresPngUrl() {
  return '/api/scores.png'
}

// Голый растр для оверлея на карте: пиксели ровно по границам площади.
// scores.png для этого не годится — у него заголовок, оси и шкала.
export function getScoresMapPngUrl() {
  return '/api/scores-map.png'
}

export function getScoresCsvUrl() {
  return '/api/scores.csv'
}

export default api