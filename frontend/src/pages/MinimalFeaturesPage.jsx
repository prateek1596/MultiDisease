import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import toast from 'react-hot-toast'
import {
  Minimize2, Play, Loader2, CheckCircle, TrendingDown,
  DollarSign, Users, Zap, FileText, AlertCircle
} from 'lucide-react'
import clsx from 'clsx'
import { getApiErrorMessage } from '../utils/apiError'

const DISEASES = ['heart', 'diabetes', 'kidney']
const DISEASE_EMOJI = { heart: '🫀', diabetes: '🩸', kidney: '🫘' }
const METRICS = ['accuracy', 'auc', 'f1']

function ImpactRow({ row }) {
  return (
    <tr className="hover:bg-slate-50">
      <td className="px-4 py-3 font-medium text-slate-800">{row.scale}</td>
      <td className="px-4 py-3 text-slate-600">{row.patients_per_year.toLocaleString()}</td>
      <td className="px-4 py-3 font-mono text-emerald-700 font-semibold">
        ${row.total_cost_savings_usd.toLocaleString()}
      </td>
      <td className="px-4 py-3 text-slate-600">{row.tests_eliminated.toLocaleString()}</td>
      <td className="px-4 py-3 text-brand-700 font-semibold">
        +{row.additional_screenings.toLocaleString()}
      </td>
      <td className="px-4 py-3">
        <span className="badge badge-green">{(row.accuracy_maintained * 100).toFixed(1)}%</span>
      </td>
    </tr>
  )
}

function FeatureImportanceBar({ feature, importance, maxImp, rank }) {
  const pct = maxImp > 0 ? (importance / maxImp) * 100 : 0
  return (
    <div className="flex items-center gap-3 py-1.5">
      <span className="w-5 text-xs text-slate-400 font-mono text-right">{rank}</span>
      <span className="w-40 text-sm text-slate-700 truncate font-medium">{feature}</span>
      <div className="flex-1 bg-slate-100 rounded-full h-2.5 overflow-hidden">
        <div className="h-full bg-brand-500 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="w-14 text-xs text-slate-500 font-mono text-right">
        {importance.toFixed(4)}
      </span>
    </div>
  )
}

export default function MinimalFeaturesPage() {
  const [disease,     setDisease]     = useState('heart')
  const [targetAcc,   setTargetAcc]   = useState(0.85)
  const [targetMetric,setTargetMetric]= useState('accuracy')
  const [costPerTest, setCostPerTest] = useState(10)
  const [genProtocol, setGenProtocol] = useState(false)
  const [result,      setResult]      = useState(null)

  const mutation = useMutation({
    mutationFn: () =>
      api.post(`/minimal-features/${disease}`, {
        target_accuracy:   targetAcc,
        target_metric:     targetMetric,
        cost_per_test_usd: costPerTest,
        generate_protocol: genProtocol,
      }).then(r => r.data),
    onSuccess: (data) => {
      setResult(data)
      if (data.status === 'not_achievable') {
        toast.error(data.message)
      } else {
        toast.success('Analysis complete!')
      }
    },
    onError: (err) => toast.error(getApiErrorMessage(err, 'Analysis failed')),
  })

  const cfg = result?.minimal_config
  const maxImp = cfg ? Math.max(...Object.values(cfg.feature_importances)) : 1

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <Minimize2 className="w-8 h-8 text-brand-600" /> Minimal Feature Analysis
        </h1>
        <p className="text-slate-500 mt-1">
          Find the smallest diagnostic test set that maintains target accuracy — for resource-constrained settings
        </p>
      </div>

      {/* Config */}
      <div className="card p-6 space-y-5">
        <h2 className="font-bold text-slate-900">Configuration</h2>

        {/* Disease selector */}
        <div>
          <label className="block text-sm font-semibold text-slate-600 mb-2">Disease Dataset</label>
          <div className="flex gap-3 flex-wrap">
            {DISEASES.map(d => (
              <button key={d} onClick={() => { setDisease(d); setResult(null) }}
                className={clsx(
                  'px-4 py-2 rounded-xl border-2 text-sm font-semibold transition-all',
                  disease === d
                    ? 'border-brand-500 bg-brand-50 text-brand-700'
                    : 'border-slate-200 text-slate-500 hover:border-slate-300'
                )}>
                {DISEASE_EMOJI[d]} {d.charAt(0).toUpperCase() + d.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="grid sm:grid-cols-3 gap-4">
          {/* Target metric */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Optimise By</label>
            <div className="relative">
              <select value={targetMetric} onChange={e => setTargetMetric(e.target.value)}
                className="input-field appearance-none pr-8 cursor-pointer">
                {METRICS.map(m => (
                  <option key={m} value={m}>{m.toUpperCase()}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Target value */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">
              Target {targetMetric.toUpperCase()}: <span className="text-brand-600">{(targetAcc * 100).toFixed(0)}%</span>
            </label>
            <input type="range" min={0.60} max={0.98} step={0.01} value={targetAcc}
              onChange={e => setTargetAcc(parseFloat(e.target.value))}
              className="w-full accent-brand-600 mt-2" />
          </div>

          {/* Cost per test */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">
              Cost per Test (USD)
            </label>
            <input type="number" min={1} max={500} value={costPerTest}
              onChange={e => setCostPerTest(Number(e.target.value))}
              className="input-field" />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input type="checkbox" id="genProto" checked={genProtocol}
            onChange={e => setGenProtocol(e.target.checked)}
            className="w-4 h-4 accent-brand-600" />
          <label htmlFor="genProto" className="text-sm font-medium text-slate-700">
            Generate deployment protocol (Markdown)
          </label>
        </div>

        <button onClick={() => mutation.mutate()} disabled={mutation.isPending}
          className="btn-primary flex items-center gap-2">
          {mutation.isPending
            ? <><Loader2 className="w-4 h-4 animate-spin" />Analysing…</>
            : <><Play className="w-4 h-4" />Find Minimal Feature Set</>}
        </button>
      </div>

      {/* Result */}
      {result?.status === 'not_achievable' && (
        <div className="card p-5 border-2 border-amber-300 bg-amber-50 flex items-center gap-3">
          <AlertCircle className="w-8 h-8 text-amber-500 flex-shrink-0" />
          <div>
            <p className="font-bold text-amber-800">Target Not Achievable</p>
            <p className="text-sm text-amber-700">{result.message}</p>
            <p className="text-sm text-amber-600 mt-1">Try lowering the target or switching to a different metric.</p>
          </div>
        </div>
      )}

      {cfg && (
        <div className="space-y-5 animate-in">
          {/* Summary hero */}
          <div className="card p-6 bg-gradient-to-r from-brand-900 to-brand-700 text-white">
            <div className="grid sm:grid-cols-4 gap-5">
              {[
                { icon: Zap,         label: 'Features Required', value: `${cfg.n_features}` },
                { icon: TrendingDown,label: 'Tests Reduced',     value: `${cfg.reduction_pct.toFixed(1)}%` },
                { icon: CheckCircle, label: `${targetMetric.toUpperCase()} Maintained`, value: `${(cfg[targetMetric] * 100).toFixed(2)}%` },
                { icon: DollarSign,  label: 'Saved / Patient',   value: `$${((cfg.feature_importances ? Object.keys(cfg.feature_importances).length : 0) * costPerTest).toFixed(0)}` },
              ].map(({ icon: Icon, label, value }) => (
                <div key={label} className="text-center">
                  <Icon className="w-6 h-6 text-brand-200 mx-auto mb-2" />
                  <p className="text-3xl font-bold text-white">{value}</p>
                  <p className="text-xs text-brand-300 mt-1">{label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Detailed metrics */}
          <div className="grid sm:grid-cols-3 gap-4">
            {[
              { label: 'Accuracy',          val: cfg.accuracy,          base: cfg.baseline_accuracy },
              { label: 'AUC-ROC',           val: cfg.auc,               base: cfg.baseline_auc      },
              { label: 'F1-Score',          val: cfg.f1,                base: null                  },
            ].map(({ label, val, base }) => (
              <div key={label} className="card p-4">
                <p className="text-xs font-semibold text-slate-500 mb-1">{label}</p>
                <p className="text-2xl font-bold text-slate-900 font-mono">{(val * 100).toFixed(2)}%</p>
                {base != null && (
                  <p className="text-xs text-slate-400 mt-1">
                    Baseline: {(base * 100).toFixed(2)}%
                    &nbsp;
                    <span className={clsx(
                      'font-semibold',
                      val >= base ? 'text-emerald-600' : 'text-amber-600'
                    )}>
                      ({val >= base ? '+' : ''}{((val - base) * 100).toFixed(2)} pp)
                    </span>
                  </p>
                )}
              </div>
            ))}
          </div>

          {/* Feature list */}
          <div className="card p-5">
            <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-500" />
              Required Features ({cfg.n_features})
              <span className="badge badge-blue text-[11px]">by importance</span>
            </h3>
            <div className="space-y-0.5">
              {Object.entries(cfg.feature_importances)
                .sort((a, b) => b[1] - a[1])
                .map(([feat, imp], i) => (
                  <FeatureImportanceBar
                    key={feat}
                    feature={feat}
                    importance={imp}
                    maxImp={maxImp}
                    rank={i + 1}
                  />
                ))}
            </div>
          </div>

          {/* Impact table */}
          {result.impact_analysis?.length > 0 && (
            <div className="card overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
                <Users className="w-4 h-4 text-slate-500" />
                <h3 className="font-bold text-slate-900">Economic & Healthcare Impact</h3>
                <span className="text-xs text-slate-400">at ${costPerTest} / test</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase">
                    <tr>
                      {['Scale','Patients/Year','Cost Savings','Tests Eliminated','Extra Screenings','Accuracy'].map(h => (
                        <th key={h} className="px-4 py-3 text-left">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {result.impact_analysis.map((row, i) => (
                      <ImpactRow key={i} row={row} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Protocol note */}
          {result.protocol_path && (
            <div className="card p-4 bg-emerald-50 border border-emerald-200 flex items-center gap-3">
              <FileText className="w-5 h-5 text-emerald-600 flex-shrink-0" />
              <div>
                <p className="text-sm font-semibold text-emerald-800">Deployment Protocol Generated</p>
                <p className="text-xs text-emerald-700 font-mono mt-0.5">{result.protocol_path}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
