import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Activity, Heart, Zap, TrendingUp, ArrowRight, Award } from 'lucide-react'
import { modelsAPI } from '../api/client'
import { useAuthStore } from '../store/authStore'

const DiseaseCard = ({ emoji, color, label, description, bestModel, bestAuc, onClick }) => {
  const colorMap = {
    heart:    'from-red-50 to-rose-50 border-red-200 hover:border-red-300',
    diabetes: 'from-yellow-50 to-amber-50 border-yellow-200 hover:border-yellow-300',
    kidney:   'from-emerald-50 to-teal-50 border-emerald-200 hover:border-emerald-300',
  }
  const accentMap = {
    heart:    'bg-red-100 text-red-600',
    diabetes: 'bg-yellow-100 text-yellow-600',
    kidney:   'bg-emerald-100 text-emerald-600',
  }
  return (
    <button onClick={onClick}
      className={`w-full text-left card bg-gradient-to-br ${colorMap[color]} border p-6 hover:shadow-md transition-all duration-200 group`}>
      <div className="flex items-start justify-between mb-4">
        <div className={`w-12 h-12 rounded-2xl ${accentMap[color]} flex items-center justify-center text-2xl`}>
          {emoji}
        </div>
        <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-slate-600 group-hover:translate-x-1 transition-all" />
      </div>
      <h3 className="font-bold text-slate-900 text-lg">{label}</h3>
      <p className="text-sm text-slate-500 mt-1 mb-4">{description}</p>
      {bestModel ? (
        <div className="flex items-center gap-2 pt-3 border-t border-slate-200/60">
          <Award className="w-3.5 h-3.5 text-amber-500" />
          <span className="text-xs text-slate-500">
            Best: <span className="font-semibold text-slate-700">{bestModel}</span>
            {bestAuc && <span className="text-slate-400"> · AUC {bestAuc}</span>}
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-2 pt-3 border-t border-slate-200/60">
          <span className="text-xs text-slate-400 italic">Train models to see metrics</span>
        </div>
      )}
    </button>
  )
}

const StatCard = ({ icon: Icon, label, value, sub, color }) => (
  <div className="card p-5">
    <div className="flex items-center gap-3 mb-3">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${color}`}>
        <Icon className="w-[18px] h-[18px]" />
      </div>
      <span className="text-sm font-medium text-slate-500">{label}</span>
    </div>
    <p className="text-3xl font-bold text-slate-900">{value}</p>
    {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
  </div>
)

export default function DashboardPage() {
  const navigate = useNavigate()
  const user = useAuthStore(s => s.user)

  const { data: perfData } = useQuery({
    queryKey: ['performance'],
    queryFn: () => modelsAPI.performance().then(r => r.data),
    retry: false,
    // Don't throw on error — gracefully show empty state
    throwOnError: false,
  })

  const getBest = (disease) => {
    const diseaseData = perfData?.[disease]
    if (!diseaseData || Object.keys(diseaseData).length === 0) return {}
    const entries = Object.entries(diseaseData).filter(([, m]) => m && typeof m === 'object' && m.roc_auc)
    if (!entries.length) return {}
    const best = entries.reduce((a, b) => (a[1].roc_auc > b[1].roc_auc ? a : b))
    return {
      model: best[0].replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      auc:   best[1].roc_auc?.toFixed(3),
    }
  }

  const heartBest    = getBest('heart')
  const diabetesBest = getBest('diabetes')
  const kidneyBest   = getBest('kidney')

  const hasAnyMetrics = heartBest.auc || diabetesBest.auc || kidneyBest.auc
  const bestAucValue  = hasAnyMetrics
    ? Math.max(
        parseFloat(heartBest.auc    || 0),
        parseFloat(diabetesBest.auc || 0),
        parseFloat(kidneyBest.auc   || 0),
      ).toFixed(3)
    : '—'

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900">
          Welcome back, <span className="text-brand-600">{user?.username}</span> 👋
        </h1>
        <p className="text-slate-500 mt-1">
          Multi-Disease Prediction System — powered by 6 ML models across 3 disease datasets
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Activity}   label="Diseases Covered" value="3"   sub="Heart · Diabetes · Kidney"         color="bg-brand-50 text-brand-600" />
        <StatCard icon={Zap}        label="ML Models"        value="6"   sub="LR · RF · SVM · XGB · LGBM · Stack" color="bg-purple-50 text-purple-600" />
        <StatCard icon={TrendingUp} label="Best AUC"         value={bestAucValue} sub="Across all models"        color="bg-emerald-50 text-emerald-600" />
        <StatCard icon={Heart}      label="Predictions Run"  value="—"   sub="See Analytics page"                 color="bg-rose-50 text-rose-600" />
      </div>

      {/* No-models warning */}
      {!hasAnyMetrics && (
        <div className="rounded-xl bg-amber-50 border border-amber-200 p-4 flex items-start gap-3">
          <span className="text-amber-500 text-xl flex-shrink-0">⚠️</span>
          <div>
            <p className="text-sm font-semibold text-amber-800">No trained models found</p>
            <p className="text-sm text-amber-700 mt-0.5">
              Go to <strong>Train Models</strong> (admin) to train all 6 ML models, or run{' '}
              <code className="bg-amber-100 px-1 rounded text-xs">python scripts/train_all.py</code>{' '}
              from the backend directory. Predictions will still work after training.
            </p>
          </div>
        </div>
      )}

      {/* Disease cards */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-slate-900">Select a Disease to Predict</h2>
          <button onClick={() => navigate('/predict')} className="btn-primary flex items-center gap-2 text-sm">
            <Activity className="w-4 h-4" /> Start Prediction
          </button>
        </div>
        <div className="grid md:grid-cols-3 gap-5">
          <DiseaseCard emoji="🫀" color="heart"    label="Heart Disease"
            description="Cleveland Heart Disease dataset — 13 clinical features"
            bestModel={heartBest.model} bestAuc={heartBest.auc}
            onClick={() => navigate('/predict?disease=heart')} />
          <DiseaseCard emoji="🩸" color="diabetes" label="Diabetes"
            description="PIMA Indians Diabetes dataset — 8 metabolic features"
            bestModel={diabetesBest.model} bestAuc={diabetesBest.auc}
            onClick={() => navigate('/predict?disease=diabetes')} />
          <DiseaseCard emoji="🫘" color="kidney"   label="Kidney Disease"
            description="UCI CKD dataset — 24 clinical & laboratory features"
            bestModel={kidneyBest.model} bestAuc={kidneyBest.auc}
            onClick={() => navigate('/predict?disease=kidney')} />
        </div>
      </div>

      {/* How it works banner */}
      <div className="card p-6 bg-gradient-to-r from-brand-900 to-brand-700 text-white">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-bold text-lg mb-1">How It Works</h3>
            <p className="text-brand-200 text-sm max-w-lg">
              Enter patient clinical data → choose a disease → select a model (or let the system
              auto-select the best one). Predictions include probability scores, risk bands,
              SHAP explanations, and downloadable clinical PDF reports.
            </p>
          </div>
          <Activity className="w-10 h-10 text-brand-300 opacity-60 hidden md:block" />
        </div>
        <div className="flex flex-wrap gap-2 mt-4">
          {['SMOTE Balancing','SHAP Explainability','Risk Scoring','6 ML Models','PDF Reports',
            'Fairness Analysis','What-If Explorer','AutoML Tuning','A/B Testing'].map(tag => (
            <span key={tag} className="px-3 py-1 bg-white/10 rounded-full text-xs font-medium text-brand-100">
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
