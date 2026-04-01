import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
})

// Attach JWT token
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle 401 globally
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ─── Auth ─────────────────────────────────────────────────────
export const authAPI = {
  login:    (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  me:       ()     => api.get('/auth/me'),
}

// ─── Prediction ───────────────────────────────────────────────
export const predictAPI = {
  predict: (disease, payload) => api.post(`/predict/${disease}`, payload),
  history: (disease, limit = 50) =>
    api.get('/predictions/history', { params: { disease, limit } }),
}

// ─── Models ───────────────────────────────────────────────────
export const modelsAPI = {
  performance:    ()        => api.get('/models/performance'),
  diseasePerf:    (disease) => api.get(`/models/performance/${disease}`),
  comparison:     ()        => api.get('/models/comparison'),
}

// ─── Training ─────────────────────────────────────────────────
export const trainAPI = {
  start:  (payload) => api.post('/train', payload),
  status: ()        => api.get('/train/status'),
}

// ─── Reports ──────────────────────────────────────────────────
export const reportAPI = {
  download: () => api.get('/report/download', { responseType: 'blob' }),
  list:     () => api.get('/report/list'),
}
