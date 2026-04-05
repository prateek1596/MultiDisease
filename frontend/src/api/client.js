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

// Handle 401 globally; normalise error detail to always be a string
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }

    // Normalise Pydantic 422 detail array → plain string so toast never crashes
    const detail = err.response?.data?.detail
    if (Array.isArray(detail)) {
      err.response.data.detail = detail
        .map(d => {
          const field = Array.isArray(d.loc) ? d.loc.slice(1).join(' → ') : ''
          return field ? `${field}: ${d.msg}` : d.msg
        })
        .join(' · ')
    }

    return Promise.reject(err)
  }
)

// ─── Auth ──────────────────────────────────────────────────────────────────
export const authAPI = {
  login:    (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  me:       ()     => api.get('/auth/me'),
}

// ─── Prediction ────────────────────────────────────────────────────────────
export const predictAPI = {
  predict: (disease, payload) => api.post(`/predict/${disease}`, payload),
  history: (disease, limit = 50) =>
    api.get('/predictions/history', { params: { disease, limit } }),
}

// ─── Models ────────────────────────────────────────────────────────────────
export const modelsAPI = {
  performance: ()        => api.get('/models/performance'),
  diseasePerf: (disease) => api.get(`/models/performance/${disease}`),
  comparison:  ()        => api.get('/models/comparison'),
}

// ─── Training ──────────────────────────────────────────────────────────────
export const trainAPI = {
  start:  (payload) => api.post('/train', payload),
  status: ()        => api.get('/train/status'),
}

// ─── Reports ───────────────────────────────────────────────────────────────
export const reportAPI = {
  download: () => api.get('/report/download', { responseType: 'blob' }),
  list:     () => api.get('/report/list'),
}

// ─── Advanced APIs ─────────────────────────────────────────────────────────
export const analyticsAPI = {
  get: () => api.get('/analytics'),
}

export const riskAPI = {
  bands: (disease) => api.get(`/risk-bands/${disease}`),
}

export const cacheAPI = {
  stats:    ()        => api.get('/cache/stats'),
  flush:    (disease) => api.delete(`/cache/flush/${disease}`),
  flushAll: ()        => api.delete('/cache/flush-all'),
}

export const automlAPI = {
  tune:    (payload) => api.post('/automl/tune', payload),
  results: (disease) => api.get(`/automl/results/${disease}`),
}

export const counterfactualAPI = {
  get: (disease, payload) => api.post(`/counterfactual/${disease}`, payload),
}

export const abAPI = {
  configure: (disease, payload) => api.post(`/ab/${disease}/configure`, payload),
  status:    (disease)          => api.get(`/ab/${disease}/status`),
  analyse:   (disease)          => api.get(`/ab/${disease}/analyse`),
  clear:     (disease)          => api.delete(`/ab/${disease}/clear`),
}

export const patientReportAPI = {
  generate: (payload) =>
    api.post('/patient-report', payload, { responseType: 'blob' }),
}
