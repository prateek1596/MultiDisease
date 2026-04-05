import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import { DISEASES } from '../utils/diseaseConfig'
import toast from 'react-hot-toast'
import { Wand2, Play, Loader2, ArrowRight, TrendingDown, TrendingUp, CheckCircle, XCircle } from 'lucide-react'
import clsx from 'clsx'

const DISEASE_EMOJI = { heart: '🫀', diabetes: '🩸', kidney: '🫘' }

function ChangeRow({ change }) {
  const up = change.delta > 0
  return (
    <div className="flex items-center gap-3 py-2 border-b border-slate-100 last:border-0">
      <span className="w-40 text-sm font-medium text-slate-700 truncate">
        {change.feature.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}
      </span>
      <span className="font-mono text-sm text-slate-500">{change.original}</span>
      <ArrowRight className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
      <span className={clsx('font-mono text-sm font-semibold', up ? 'text-red-600' : 'text-emerald-600')}>
        {change.counterfactual}
      </span>
      <span className={clsx('ml-auto flex items-center gap-1 text-xs font-semibold', up ? 'text-red-500' : 'text-emerald-500')}>
        {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
        {up ? '+' : ''}{change.delta.toFixed(4)}
      </span>
    </div>
  )
}

function CFCard({ cf, index, disease }) {
  const flipped = cf.new_prediction === 0
  return (
    <div className={clsx(
      'card p-5 border-l-4',
      flipped ? 'border-emerald-400' : 'border-red-400'
    )}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-bold text-slate-700">
          Option {index + 1} — {cf.features_changed} feature{cf.features_changed !== 1 ? 's' : ''} changed
        </span>
        <div className="flex items-center gap-2">
          {flipped
            ? <CheckCircle className="w-4 h-4 text-emerald-500" />
            : <XCircle    className="w-4 h-4 text-red-500" />}
          <span className={clsx('text-xs font-bold', flipped ? 'text-emerald-600' : 'text-red-600')}>
            {(cf.new_probability * 100).toFixed(1)}% confidence
          </span>
        </div>
      </div>
      <div>
        {cf.changes.map((c, i) => <ChangeRow key={i} change={c} />)}
      </div>
    </div>
  )
}

export default function CounterfactualPage() {
  const [searchParams] = useSearchParams()
  const [disease, setDisease]   = useState(searchParams.get('disease') || 'heart')
  const [inputJson, setInputJson] = useState('')
  const [result, setResult]     = useState(null)
  const [jsonError, setJsonError] = useState('')

  const mutation = useMutation({
    mutationFn: () => {
      let parsed
      try { parsed = JSON.parse(inputJson); setJsonError('') }
      catch { setJsonError('Invalid JSON'); throw new Error('Invalid JSON') }
      return api.post(`/counterfactual/${disease}`, {
        input_data: parsed, model_name: 'best', n_counterfactuals: 3
      }).then(r => r.data)
    },
    onSuccess: data => { setResult(data); toast.success('Counterfactuals found!') },
    onError: err => toast.error(err.response?.data?.detail || err.message || 'Failed'),
  })

  const diseaseConfig = DISEASES[disease]
  const exampleInput = Object.fromEntries(
    diseaseConfig.fields.map(f => [
      f.name,
      f.type === 'select' ? f.options?.[0]?.value ?? 0 : parseFloat(f.placeholder ?? 0) || 0
    ])
  )

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <Wand2 className="w-8 h-8 text-brand-600" /> What-If Explorer
        </h1>
        <p className="text-slate-500 mt-1">
          Find the minimal input changes that would flip a prediction outcome
        </p>
      </div>

      <div className="card p-6 space-y-5">
        <div>
          <label className="block text-sm font-semibold text-slate-600 mb-2">Disease</label>
          <div className="flex gap-3 flex-wrap">
            {Object.keys(DISEASES).map(d => (
              <button key={d} onClick={() => { setDisease(d); setResult(null) }}
                className={clsx(
                  'px-4 py-2 rounded-xl border-2 text-sm font-semibold transition-all',
                  disease === d ? 'border-brand-500 bg-brand-50 text-brand-700' : 'border-slate-200 text-slate-500'
                )}>
                {DISEASE_EMOJI[d]} {d.charAt(0).toUpperCase() + d.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-xs font-semibold text-slate-600">
              Patient Input (JSON)
            </label>
            <button
              onClick={() => setInputJson(JSON.stringify(exampleInput, null, 2))}
              className="text-xs text-brand-600 hover:underline font-medium">
              Load example
            </button>
          </div>
          <textarea
            value={inputJson}
            onChange={e => setInputJson(e.target.value)}
            rows={8}
            className={clsx(
              'w-full px-3.5 py-2.5 rounded-xl border font-mono text-xs',
              'bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/30',
              jsonError ? 'border-red-400' : 'border-slate-200 focus:border-brand-500'
            )}
            placeholder='{"age": 54, "glucose": 148, ...}'
          />
          {jsonError && <p className="text-xs text-red-500 mt-1">{jsonError}</p>}
        </div>

        <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800">
          Paste a patient's feature values as JSON (same fields as the Predict form).
          The system will find which minimal changes would flip the model's decision.
        </div>

        <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !inputJson.trim()}
          className="btn-primary flex items-center gap-2">
          {mutation.isPending
            ? <><Loader2 className="w-4 h-4 animate-spin" />Searching…</>
            : <><Play className="w-4 h-4" />Find Counterfactuals</>}
        </button>
      </div>

      {result && (
        <div className="space-y-4 animate-in">
          {/* Summary */}
          <div className="card p-5 bg-slate-50">
            <div className="flex items-center gap-4">
              <div className={clsx(
                'w-12 h-12 rounded-2xl flex items-center justify-center text-xl',
                result.original_prediction === 1 ? 'bg-red-100' : 'bg-emerald-100'
              )}>
                {result.original_prediction === 1 ? '⚠️' : '✅'}
              </div>
              <div>
                <p className="font-bold text-slate-900">
                  Original: {result.original_prediction === 1 ? 'Positive' : 'Negative'}
                  <span className="font-normal text-slate-500 ml-2">
                    ({(result.original_probability * 100).toFixed(1)}% confidence)
                  </span>
                </p>
                <p className="text-sm text-slate-500 mt-0.5">
                  {result.counterfactuals.length} counterfactual(s) found via <code className="bg-slate-200 px-1 rounded text-xs">{result.method}</code>
                </p>
              </div>
            </div>
          </div>

          {result.counterfactuals.length === 0 ? (
            <div className="card p-8 text-center">
              <p className="text-slate-500">No counterfactuals found. The model is very confident in this prediction.</p>
            </div>
          ) : (
            <div className="space-y-3">
              <h3 className="font-bold text-slate-900">
                Counterfactual Explanations — changes that would flip the prediction:
              </h3>
              {result.counterfactuals.map((cf, i) => (
                <CFCard key={i} cf={cf} index={i} disease={disease} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
