import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/Layout/Layout'
import DashboardPage       from './pages/DashboardPage'
import PredictPage         from './pages/PredictPage'
import PerformancePage     from './pages/PerformancePage'
import HistoryPage         from './pages/HistoryPage'
import TrainPage           from './pages/TrainPage'
import FairnessPage        from './pages/FairnessPage'
import MinimalFeaturesPage from './pages/MinimalFeaturesPage'
import AnalyticsPage       from './pages/AnalyticsPage'
import CounterfactualPage  from './pages/CounterfactualPage'
import ABTestingPage       from './pages/ABTestingPage'
import AutoMLPage          from './pages/AutoMLPage'
import LoginPage           from './pages/LoginPage'
import RegisterPage        from './pages/RegisterPage'

function PrivateRoute({ children }) {
  const ok = useAuthStore(s => s.isAuthenticated)
  return ok ? children : <Navigate to="/login" replace />
}
function AdminRoute({ children }) {
  const user = useAuthStore(s => s.user)
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
        <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
          <Route index                   element={<DashboardPage />} />
          <Route path="predict"          element={<PredictPage />} />
          <Route path="performance"      element={<PerformancePage />} />
          <Route path="history"          element={<HistoryPage />} />
          <Route path="fairness"         element={<FairnessPage />} />
          <Route path="minimal"          element={<MinimalFeaturesPage />} />
          <Route path="analytics"        element={<AnalyticsPage />} />
          <Route path="counterfactual"   element={<CounterfactualPage />} />
          <Route path="ab-testing"       element={<AdminRoute><ABTestingPage /></AdminRoute>} />
          <Route path="automl"           element={<AdminRoute><AutoMLPage /></AdminRoute>} />
          <Route path="train"            element={<AdminRoute><TrainPage /></AdminRoute>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
