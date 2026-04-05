import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import toast from 'react-hot-toast'
import { FlaskConical, Play, BarChart2, Trash2, Loader2, CheckCircle, AlertTriangle, Info } from 'lucide-react'
import clsx from 'clsx'

const DISEASES = ['heart', 'diabetes', 'kidney']
const MODELS   = ['logistic_regression','random_forest','svm','xgboost','lightgbm']
const DISEASE_EMOJI = { heart: '🫀', diabetes: '🩸', kidney: '🫘' }

function StatBox({ label, value, sub }) {
  return (
    <div className="bg-slate-50 rounded-xl p-4">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className="text-xl font-bold text-slate-900 font-mono">{value ?? '—'}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  )
}

export default function ABTestingPage() {
  const qc = useQueryClient()
  const [disease, setDisease]   = useState('heart')
  const [modelA,  setModelA]    = useState('random_forest')
  const [modelB,  setModelB]    = useState('xgboost')
  const [minSamples, setMinSamples] = useState(30)
  const [analysis, setAnalysis] = useState(null)

  const { data: statusData, refetch: refetchStatus } = useQuery({
    queryKey: ['ab-status', disease],
    queryFn: () => api.get(`/ab/${disease}/status`).then(r => r.data),
    retry: false,
  })

  const configureMut = useMutation({
    mutationFn: () => api.post(`/ab/${disease}/configure`, {
      model_a: modelA, model_b: modelB, enabled: true, min_samples: minSamples
    }).then(r => r.data),
    onSuccess: () => { toast.success('A/B test configured!'); refetchStatus() },
    onError: err => toast.error(err.response?.data?.detail || 'Failed'),
  })

  const analyseMut = useMutation({
    mutationFn: () => api.get(`/ab/${disease}/analyse`).then(r => r.data),
    onSuccess: data => { setAnalysis(data); toast.success('Analysis complete!') },
    onError: err => toast.error(err.response?.data?.detail || 'Insufficient data'),
  })

  const clearMut = useMutation({
    mutationFn: () => api.delete(`/ab/${disease}/clear`).then(r => r.data),
    onSuccess: () => { toast.success('Log cleared'); refetchStatus(); setAnalysis(null) },
  })

  const summary = statusData?.summary ?? {}
  const config  = statusData?.config

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <FlaskConical className="w-8 h-8 text-brand-600" /> A/B Shadow Testing
        </h1>
        <p className="text-slate-500 mt-1">
          Silently run two models on every prediction, then compare with a paired t-test
        </p>
      </div>

      <div className="rounded-xl bg-blue-50 border border-blue-200 p-4 flex gap-3 text-sm text-blue-800">
        <Info className="w-5 h-5 flex-shrink-0 mt-0.5 text-blue-500" />
        <p>When enabled, every prediction secretly runs Model B alongside Model A. After enough samples, use the Analyse button to run a paired t-test and get a statistically-grounded recommendation.</p>
      </div>

      {/* Config */}
      <div className="card p-6 space-y-5">
        <h2 className="font-bold text-slate-900">Configure Test</h2>

        <div className="flex gap-3 flex-wrap">
          {DISEASES.map(d => (
            <button key={d} onClick={() => { setDisease(d); setAnalysis(null) }}
              className={clsx(
                'px-4 py-2 rounded-xl border-2 text-sm font-semibold transition-all',
                disease === d ? 'border-brand-500 bg-brand-50 text-brand-700' : 'border-slate-200 text-slate-500'
              )}>
              {DISEASE_EMOJI[d]} {d.charAt(0).toUpperCase() + d.slice(1)}
            </button>
          ))}
        </div>

        <div className="grid sm:grid-cols-3 gap-4">
          {[
            { label: 'Model A (primary)', val: modelA, set: setModelA },
            { label: 'Model B (shadow)',  val: modelB, set: setModelB },
          ].map(({ label, val, set }) => (
            <div key={label}>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5">{label}</label>
              <select value={val} onChange={e => set(e.target.value)} className="input-field appearance-none">
                {MODELS.map(m => <option key={m} value={m}>{m.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</option>)}
              </select>
            </div>
          ))}
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Min samples before analysis</label>
            <input type="number" min={10} max={500} value={minSamples}
              onChange={e => setMinSamples(Number(e.target.value))}
              className="input-field" />
          </div>
        </div>

        <div className="flex gap-3 flex-wrap">
          <button onClick={() => configureMut.mutate()} disabled={configureMut.isPending}
            className="btn-primary flex items-center gap-2 text-sm">
            {configureMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Enable A/B Test
          </button>
          <button onClick={() => analyseMut.mutate()} disabled={analyseMut.isPending || !config}
            className="btn-secondary flex items-center gap-2 text-sm">
            {analyseMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart2 className="w-4 h-4" />}
            Run Analysis
          </button>
          <button onClick={() => clearMut.mutate()} disabled={clearMut.isPending || !config}
            className="btn-secondary flex items-center gap-2 text-sm text-red-600 hover:bg-red-50">
            <Trash2 className="w-4 h-4" /> Clear Log
          </button>
        </div>
      </div>

      {/* Status */}
      {config && (
        <div className="card p-5">
          <h3 className="font-bold text-slate-900 mb-3">Current Test Status</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatBox label="Model A" value={config.model_a?.replace(/_/g,' ')} />
            <StatBox label="Model B" value={config.model_b?.replace(/_/g,' ')} />
            <StatBox label="Samples Logged" value={summary.n ?? 0} sub={`Need ${config.min_samples} for analysis`} />
            <StatBox label="Agreement Rate" value={summary.agreement_pct != null ? `${summary.agreement_pct}%` : '—'} />
          </div>
          <div className={clsx('mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold',
            config.enabled ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500')}>
            <span className={clsx('w-2 h-2 rounded-full', config.enabled ? 'bg-emerald-500' : 'bg-slate-400')} />
            {config.enabled ? 'Shadow testing ACTIVE' : 'Disabled'}
          </div>
        </div>
      )}

      {/* Analysis results */}
      {analysis && (
        <div className="card p-6 animate-in space-y-4">
          <div className="flex items-center gap-3">
            {analysis.significant_005
              ? <CheckCircle className="w-6 h-6 text-emerald-500" />
              : <AlertTriangle className="w-6 h-6 text-amber-500" />}
            <h3 className="font-bold text-slate-900 text-lg">
              {analysis.status === 'insufficient_data' ? 'Not enough data' : 'Statistical Analysis'}
            </h3>
          </div>

          {analysis.status === 'insufficient_data' ? (
            <p className="text-slate-500">{analysis.message}</p>
          ) : (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <StatBox label={`Avg prob — ${analysis.model_a}`} value={analysis.mean_prob_a?.toFixed(4)} />
                <StatBox label={`Avg prob — ${analysis.model_b}`} value={analysis.mean_prob_b?.toFixed(4)} />
                <StatBox label="t-statistic" value={analysis.t_statistic?.toFixed(4)} />
                <StatBox label="p-value" value={analysis.p_value?.toFixed(6)}
                  sub={analysis.significant_005 ? 'Significant (p < 0.05)' : 'Not significant'} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <StatBox label="Mean Difference" value={analysis.mean_difference?.toFixed(4)} />
                <StatBox label="Agreement Rate" value={`${(analysis.agreement_rate * 100).toFixed(1)}%`}
                  sub="Both models same prediction" />
              </div>
              <div className={clsx(
                'p-4 rounded-xl border font-medium text-sm',
                analysis.significant_005
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                  : 'bg-amber-50 border-amber-300 text-amber-800'
              )}>
                🎯 {analysis.recommendation}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
