import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/Layout/Layout'
import DashboardPage    from './pages/DashboardPage'
import PredictPage      from './pages/PredictPage'
import PerformancePage  from './pages/PerformancePage'
import HistoryPage      from './pages/HistoryPage'
import TrainPage        from './pages/TrainPage'
import FairnessPage     from './pages/FairnessPage'
import MinimalFeaturesPage from './pages/MinimalFeaturesPage'
import PerformanceCurvesPage from './pages/PerformanceCurvesPage'
import FeatureImportancePage from './pages/FeatureImportancePage'
import BatchPredictionPage from './pages/BatchPredictionPage'
import MultiLabelPredictionPage from './pages/MultiLabelPredictionPage'
import UncertaintyQuantificationPage from './pages/UncertaintyQuantificationPage'
import ClinicalDecisionRulesPage from './pages/ClinicalDecisionRulesPage'
import LongitudinalTrackingPage from './pages/LongitudinalTrackingPage'
import MLflowTrackingPage from './pages/MLflowTrackingPage'
import LoginPage        from './pages/LoginPage'
import RegisterPage     from './pages/RegisterPage'

function PrivateRoute({ children }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

function AdminRoute({ children }) {
  const user = useAuthStore((s) => s.user)
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'admin') return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/"
          element={<PrivateRoute><Layout /></PrivateRoute>}
        >
          <Route index                element={<DashboardPage />} />
          <Route path="predict"       element={<PredictPage />} />
          <Route path="performance"   element={<PerformancePage />} />
          <Route path="history"       element={<HistoryPage />} />
          <Route path="fairness"      element={<FairnessPage />} />
          <Route path="minimal"       element={<MinimalFeaturesPage />} />
          <Route path="curves"        element={<PerformanceCurvesPage />} />
          <Route path="importance"    element={<FeatureImportancePage />} />
          <Route path="batch"         element={<BatchPredictionPage />} />
          <Route path="multi-label"   element={<MultiLabelPredictionPage />} />
          <Route path="uncertainty"   element={<UncertaintyQuantificationPage />} />
          <Route path="clinical-rules" element={<ClinicalDecisionRulesPage />} />
          <Route path="tracking"      element={<LongitudinalTrackingPage />} />
          <Route path="mlflow"        element={<MLflowTrackingPage />} />
          <Route path="train"         element={<AdminRoute><TrainPage /></AdminRoute>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
