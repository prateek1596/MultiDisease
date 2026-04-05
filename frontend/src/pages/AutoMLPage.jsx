import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import toast from 'react-hot-toast'
import { Cpu, Play, Loader2, Trophy, RefreshCw, ChevronDown } from 'lucide-react'
import clsx from 'clsx'

const DISEASES = ['heart', 'diabetes', 'kidney']
const DISEASE_EMOJI = { heart: '🫀', diabetes: '🩸', kidney: '🫘' }
const MODELS = ['logistic_regression','random_forest','svm','xgboost','lightgbm']

function ParamBadge({ name, value }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-100 rounded-lg text-xs font-mono text-slate-600">
      <span className="text-slate-400">{name}:</span> {String(value)}
    </span>
  )
}

export default function AutoMLPage() {
  const [disease,  setDisease]  = useState('heart')
  const [model,    setModel]    = useState('random_forest')
  const [nTrials,  setNTrials]  = useState(30)

  const { data: results, isLoading: resultsLoading, refetch } = useQuery({
    queryKey: ['automl-results', disease],
    queryFn: () => api.get(`/automl/results/${disease}`).then(r => r.data),
    retry: false,
  })

  const tuneMut = useMutation({
    mutationFn: () => api.post('/automl/tune', {
      disease, model_name: model, n_trials: nTrials
    }).then(r => r.data),
    onSuccess: data => {
      toast.success(data.message || 'Tuning started!')
      setTimeout(() => refetch(), 5000)
    },
    onError: err => toast.error(err.response?.data?.detail || 'Failed to start tuning'),
  })

  const modelResults = results?.results ?? {}
  const sortedModels = Object.entries(modelResults).sort((a,b) => (b[1].best_value||0) - (a[1].best_value||0))

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <Cpu className="w-8 h-8 text-brand-600" /> AutoML Tuning
        </h1>
        <p className="text-slate-500 mt-1">
          Optuna Bayesian search finds optimal hyperparameters for each model
        </p>
      </div>

      <div className="card p-6 space-y-5">
        <h2 className="font-bold text-slate-900">Run Tuning</h2>

        <div>
          <label className="block text-sm font-semibold text-slate-600 mb-2">Disease</label>
          <div className="flex gap-3 flex-wrap">
            {DISEASES.map(d => (
              <button key={d} onClick={() => setDisease(d)}
                className={clsx(
                  'px-4 py-2 rounded-xl border-2 text-sm font-semibold transition-all',
                  disease === d ? 'border-brand-500 bg-brand-50 text-brand-700' : 'border-slate-200 text-slate-500'
                )}>
                {DISEASE_EMOJI[d]} {d.charAt(0).toUpperCase() + d.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Model to Tune</label>
            <div className="relative">
              <select value={model} onChange={e => setModel(e.target.value)}
                className="input-field appearance-none pr-8 cursor-pointer">
                {MODELS.map(m => (
                  <option key={m} value={m}>{m.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">
              Trials: <span className="text-brand-600 font-bold">{nTrials}</span>
            </label>
            <input type="range" min={10} max={100} value={nTrials}
              onChange={e => setNTrials(Number(e.target.value))}
              className="w-full accent-brand-600 mt-2" />
          </div>
        </div>

        <div className="rounded-xl bg-purple-50 border border-purple-200 p-3 text-xs text-purple-800">
          Runs in background. More trials = better params but longer wait. 30 trials ≈ 2–5 min.
          Results are saved and used automatically for future predictions.
        </div>

        <button onClick={() => tuneMut.mutate()} disabled={tuneMut.isPending}
          className="btn-primary flex items-center gap-2">
          {tuneMut.isPending
            ? <><Loader2 className="w-4 h-4 animate-spin" />Starting…</>
            : <><Play className="w-4 h-4" />Start Tuning ({nTrials} trials)</>}
        </button>
      </div>

      {/* Results */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="font-bold text-slate-900">Tuning Results — {disease.charAt(0).toUpperCase()+disease.slice(1)}</h3>
          <button onClick={() => refetch()} className="btn-secondary p-2">
            <RefreshCw className={clsx('w-4 h-4', resultsLoading && 'animate-spin')} />
          </button>
        </div>

        {resultsLoading ? (
          <div className="py-12 flex items-center justify-center gap-2 text-slate-400 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading…
          </div>
        ) : sortedModels.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-sm">
            No tuning results yet. Run AutoML tuning above.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {sortedModels.map(([modelName, r], idx) => (
              <div key={modelName} className={clsx('px-5 py-4', idx === 0 && 'bg-amber-50/60')}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {idx === 0 && <Trophy className="w-4 h-4 text-amber-500" />}
                    <span className="font-semibold text-slate-800 capitalize">
                      {modelName.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}
                    </span>
                    {idx === 0 && <span className="badge badge-yellow text-[11px]">Best</span>}
                  </div>
                  <span className="font-mono font-bold text-brand-600 text-sm">
                    AUC {r.best_value?.toFixed(4)}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(r.best_params || {}).map(([k, v]) => (
                    <ParamBadge key={k} name={k} value={typeof v === 'number' ? (v < 1 ? v.toFixed(4) : v) : v} />
                  ))}
                </div>
                <p className="text-xs text-slate-400 mt-2">{r.n_trials} trials</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
