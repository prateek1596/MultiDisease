import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { CheckCircle, XCircle, Zap, RotateCcw } from 'lucide-react'
import clsx from 'clsx'
import LimeExplanation from './LimeExplanation'

const DISEASE_LABELS = {
  heart:    { 0: 'No Heart Disease',    1: 'Heart Disease Detected' },
  diabetes: { 0: 'Non-Diabetic',        1: 'Diabetic' },
  kidney:   { 0: 'No Kidney Disease',   1: 'Chronic Kidney Disease Detected' },
}

export default function PredictionResult({ result, disease, onReset, limeExplanation }) {
  const isPositive = result.prediction === 1
  const label = DISEASE_LABELS[disease]?.[result.prediction] ?? result.label
  const confidence = (result.confidence * 100).toFixed(1)

  const shapData = result.explanation?.top_features?.map((f) => ({
    name: f.feature.replace(/_/g, ' '),
    value: parseFloat(f.shap_value.toFixed(4)),
    abs: parseFloat(f.abs_impact.toFixed(4)),
    direction: f.direction,
  })) ?? []

  return (
    <div className={clsx(
      'card border-2 p-6 animate-in',
      isPositive ? 'border-red-300 bg-red-50/50' : 'border-emerald-300 bg-emerald-50/50'
    )}>
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div className="flex items-center gap-4">
          <div className={clsx(
            'w-14 h-14 rounded-2xl flex items-center justify-center shadow-sm',
            isPositive ? 'bg-red-100' : 'bg-emerald-100'
          )}>
            {isPositive
              ? <XCircle className="w-8 h-8 text-red-600" />
              : <CheckCircle className="w-8 h-8 text-emerald-600" />
            }
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500 uppercase tracking-wide">Prediction Result</p>
            <h2 className={clsx(
              'text-2xl font-bold',
              isPositive ? 'text-red-700' : 'text-emerald-700'
            )}>
              {label}
            </h2>
          </div>
        </div>
        <button onClick={onReset} className="btn-secondary flex items-center gap-2 text-sm">
          <RotateCcw className="w-3.5 h-3.5" />
          New Prediction
        </button>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <p className="text-xs text-slate-500 mb-1">Confidence</p>
          <p className="text-2xl font-bold text-slate-900">{confidence}%</p>
          <div className="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={clsx('h-full rounded-full', isPositive ? 'bg-red-500' : 'bg-emerald-500')}
              style={{ width: `${confidence}%` }}
            />
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <p className="text-xs text-slate-500 mb-1">Model Used</p>
          <p className="text-sm font-bold text-slate-900 capitalize">
            {result.model_used.replace(/_/g, ' ')}
          </p>
        </div>
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <p className="text-xs text-slate-500 mb-1">Probabilities</p>
          {Object.entries(result.probability).map(([label, prob]) => (
            <div key={label} className="flex justify-between text-xs">
              <span className="text-slate-600 truncate max-w-[65%]">{label.split(' ')[0]}</span>
              <span className="font-semibold text-slate-800">{(prob * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* SHAP chart */}
      {shapData.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-amber-500" />
            <h3 className="font-bold text-slate-900 text-sm">SHAP Feature Impact</h3>
            <span className="badge badge-yellow text-[10px]">Top {shapData.length} features</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={shapData}
              layout="vertical"
              margin={{ top: 0, right: 20, left: 100, bottom: 0 }}
            >
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 11 }}
                width={95}
              />
              <Tooltip
                formatter={(v, n, p) => [
                  `${v > 0 ? '+' : ''}${v.toFixed(4)}`,
                  p.payload.direction,
                ]}
                contentStyle={{ borderRadius: 10, fontSize: 12 }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {shapData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.value > 0 ? '#ef4444' : '#10b981'}
                    fillOpacity={0.8}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="text-[11px] text-slate-400 mt-2">
            🔴 Red bars increase disease risk · 🟢 Green bars decrease risk
          </p>
        </div>
      )}

      {/* LIME Explanation */}
      {limeExplanation && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 mt-4">
          <LimeExplanation explanation={limeExplanation} />
        </div>
      )}
    </div>
  )
}
