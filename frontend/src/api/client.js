import axios from 'axios'
import { useAuthStore } from '../store/authStore'

function normalizeApiBaseUrl(rawUrl) {
  const fallback = '/api'
  const value = (rawUrl || fallback).trim()

  if (!value) return fallback

  const withoutTrailingSlash = value.replace(/\/+$/, '')
  if (/\/api$/i.test(withoutTrailingSlash)) return withoutTrailingSlash

  return `${withoutTrailingSlash}/api`
}

const BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_URL)

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

// ─── Analytics ────────────────────────────────────────────────
export const analyticsAPI = {
  // Outlier detection
  checkOutliers: (disease, inputData, zThreshold = 3.0) =>
    api.post('/analytics/outliers/check', { disease, input_data: inputData, z_threshold: zThreshold }),
  getFeatureBounds: (disease) =>
    api.get(`/analytics/outliers/bounds/${disease}`),
  
  // LIME explanations
  getLimeStatus: () => api.get('/analytics/lime/status'),
  explainWithLime: (disease, inputData, modelName = 'best', numFeatures = 10) =>
    api.post('/analytics/lime/explain', { disease, input_data: inputData, model_name: modelName, num_features: numFeatures }),
  
  // Performance curves
  getCurves: (disease, modelName = 'best') =>
    api.get(`/analytics/curves/${disease}`, { params: { model_name: modelName } }),
  compareCurves: (disease) =>
    api.get(`/analytics/curves/${disease}/compare`),
  getThresholdMetrics: (disease, threshold, modelName = 'best') =>
    api.get(`/analytics/curves/${disease}/threshold/${threshold}`, { params: { model_name: modelName } }),
  
  // Feature importance
  getFeatureImportance: (disease, modelName = 'best') =>
    api.get(`/analytics/importance/${disease}`, { params: { model_name: modelName } }),
  
  // Multi-label prediction
  predictMultiLabel: (data) =>
    api.post('/research/multi-label/predict', data),
  getComorbidityMatrix: () =>
    api.get('/research/multi-label/comorbidity-matrix'),
  
  // Uncertainty quantification
  quantifyUncertainty: (data) =>
    api.post('/research/uncertainty/quantify', data),
  getCalibration: (disease, nBins = 10) =>
    api.get(`/research/uncertainty/calibration/${disease}`, { params: { n_bins: nBins } }),
  
  // Clinical decision rules
  compareWithClinicalRules: (data) =>
    api.post('/research/clinical-rules/compare', data),
  getAvailableRules: () =>
    api.get('/research/clinical-rules/available'),
  
  // Longitudinal tracking
  listPatients: (limit = 100) =>
    api.get('/patients/', { params: { limit } }),
  getPatientHistory: (patientId, limit) =>
    api.get(`/patients/${patientId}/history`, { params: { limit } }),
  getTimelineData: (patientId) =>
    api.get(`/patients/${patientId}/timeline`),
  generateDemoPatient: (patientId = 'demo-patient-001') =>
    api.post('/patients/demo/generate', null, { params: { patient_id: patientId } }),
  
  // MLflow tracking
  getMlflowSummary: () =>
    api.get('/mlflow/summary'),
  listExperiments: () =>
    api.get('/mlflow/experiments'),
  listRuns: (experimentId) =>
    api.get('/mlflow/runs', { params: { experiment_id: experimentId } }),
  listRegisteredModels: () =>
    api.get('/mlflow/models'),
  getModelDetails: (name) =>
    api.get(`/mlflow/models/${name}`),
  transitionModelStage: (name, version, stage) =>
    api.post('/mlflow/models/transition', { name, version, stage }),
  initializeMlflowDemo: () =>
    api.post('/mlflow/demo/initialize'),
}
