import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { trainAPI } from '../api/client'
import toast from 'react-hot-toast'
import { Cpu, Play, RefreshCw, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import clsx from 'clsx'

const DISEASES = ['heart', 'diabetes', 'kidney']
const MODELS = [
  'logistic_regression', 'random_forest', 'svm',
  'xgboost', 'lightgbm', 'stacking'
]

export default function TrainPage() {
  const [selDiseases, setSelDiseases] = useState([...DISEASES])
  const [selModels, setSelModels]     = useState([...MODELS])

  const toggle = (list, setList, val) =>
    setList(list.includes(val) ? list.filter(x => x !== val) : [...list, val])

  const { data: statusData, refetch: refetchStatus } = useQuery({
    queryKey: ['trainStatus'],
    queryFn: () => trainAPI.status().then(r => r.data),
    refetchInterval: 5000,
  })

  const mutation = useMutation({
    mutationFn: () => trainAPI.start({
      diseases: selDiseases,
      models: selModels,
    }).then(r => r.data),
    onSuccess: () => {
      toast.success('Training started in background!')
      refetchStatus()
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to start training')
    },
  })

  const statusColor = {
    idle:      'badge-blue',
    running:   'badge-yellow',
    completed: 'badge-green',
    failed:    'badge-red',
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Train Models</h1>
        <p className="text-slate-500 mt-1">Admin: trigger ML training for selected diseases and models</p>
      </div>

      {/* Status */}
      {statusData && (
        <div className="card p-5 flex items-center gap-4">
          <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center', {
            'bg-blue-50':    statusData.status === 'idle',
            'bg-yellow-50':  statusData.status === 'running',
            'bg-emerald-50': statusData.status === 'completed',
            'bg-red-50':     statusData.status === 'failed',
          })}>
            {statusData.status === 'running'   && <Loader2 className="w-5 h-5 text-yellow-600 animate-spin" />}
            {statusData.status === 'completed' && <CheckCircle className="w-5 h-5 text-emerald-600" />}
            {statusData.status === 'failed'    && <XCircle className="w-5 h-5 text-red-600" />}
            {statusData.status === 'idle'      && <Cpu className="w-5 h-5 text-blue-600" />}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-800 capitalize">Training Status:</span>
              <span className={clsx('badge', statusColor[statusData.status])}>
                {statusData.status}
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-0.5">{statusData.message}</p>
          </div>
          <button onClick={() => refetchStatus()} className="btn-secondary p-2">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Disease selection */}
      <div className="card p-5">
        <h2 className="font-bold text-slate-900 mb-3">Diseases to Train</h2>
        <div className="flex flex-wrap gap-3">
          {DISEASES.map((d) => (
            <button
              key={d}
              onClick={() => toggle(selDiseases, setSelDiseases, d)}
              className={clsx(
                'px-4 py-2 rounded-xl border-2 text-sm font-semibold transition-all',
                selDiseases.includes(d)
                  ? 'border-brand-500 bg-brand-50 text-brand-700'
                  : 'border-slate-200 bg-white text-slate-500'
              )}
            >
              {d.charAt(0).toUpperCase() + d.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Model selection */}
      <div className="card p-5">
        <h2 className="font-bold text-slate-900 mb-3">Models to Train</h2>
        <div className="flex flex-wrap gap-3">
          {MODELS.map((m) => (
            <button
              key={m}
              onClick={() => toggle(selModels, setSelModels, m)}
              className={clsx(
                'px-4 py-2 rounded-xl border-2 text-sm font-semibold transition-all',
                selModels.includes(m)
                  ? 'border-purple-500 bg-purple-50 text-purple-700'
                  : 'border-slate-200 bg-white text-slate-500'
              )}
            >
              {m.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </button>
          ))}
        </div>
      </div>

      {/* Info box */}
      <div className="rounded-xl bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
        <strong>Note:</strong> Training runs in the background. Datasets are auto-generated if CSV files
        are not placed in <code className="bg-amber-100 px-1 rounded">backend/ml/data/</code>.
        Training can take 2–10 minutes depending on hardware.
      </div>

      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending || statusData?.status === 'running' || !selDiseases.length || !selModels.length}
        className="btn-primary flex items-center gap-2"
      >
        {mutation.isPending
          ? <><Loader2 className="w-4 h-4 animate-spin" />Starting…</>
          : <><Play className="w-4 h-4" />Start Training ({selDiseases.length} diseases × {selModels.length} models)</>
        }
      </button>
    </div>
  )
}
