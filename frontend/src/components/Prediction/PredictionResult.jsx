import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { api } from '../../api/client'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { CheckCircle, XCircle, Zap, RotateCcw, Download, Loader2, Wand2 } from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'

const DISEASE_LABELS = {
  heart:    { 0: 'No Heart Disease', 1: 'Heart Disease Detected' },
  diabetes: { 0: 'Non-Diabetic', 1: 'Diabetic' },
  kidney:   { 0: 'No Kidney Disease', 1: 'Chronic Kidney Disease Detected' },
}
const RISK_STYLES = {
  Low:      'bg-emerald-50 border-emerald-300 text-emerald-800',
  Medium:   'bg-yellow-50 border-yellow-300 text-yellow-800',
  High:     'bg-orange-50 border-orange-300 text-orange-800',
  Critical: 'bg-red-50 border-red-400 text-red-900',
}
const RISK_DOT = { Low:'bg-emerald-500', Medium:'bg-yellow-500', High:'bg-orange-500', Critical:'bg-red-600' }

export default function PredictionResult({ result, disease, inputData, onReset }) {
  const navigate = useNavigate()
  const [patientName, setPatientName] = useState('')
  const [showPdf, setShowPdf] = useState(false)

  const isPositive = result.prediction === 1
  const label      = DISEASE_LABELS[disease]?.[result.prediction] ?? result.label
  const confidence = (result.confidence * 100).toFixed(1)
  const risk       = result.risk ?? {}

  const shapData = (result.explanation?.top_features ?? []).map(f => ({
    name:      f.feature.replace(/_/g, ' '),
    value:     parseFloat(f.shap_value.toFixed(4)),
    direction: f.direction,
  }))

  const pdfMut = useMutation({
    mutationFn: () =>
      api.post('/patient-report', {
        prediction_data: { ...result, input_data: inputData ?? {}, disease },
        patient_name: patientName || 'Anonymous Patient',
      }, { responseType: 'blob' }).then(r => r.data),
    onSuccess: blob => {
      const url = URL.createObjectURL(blob)
      Object.assign(document.createElement('a'), { href: url, download: `report_${disease}.pdf` }).click()
      URL.revokeObjectURL(url)
      toast.success('Clinical report downloaded!')
      setShowPdf(false)
    },
    onError: () => toast.error('Report generation failed'),
  })

  return (
    <div className={clsx(
      'card border-2 p-6 animate-in',
      isPositive ? 'border-red-300 bg-red-50/40' : 'border-emerald-300 bg-emerald-50/40'
    )}>
      {/* Header row */}
      <div className="flex items-start justify-between mb-5 flex-wrap gap-3">
        <div className="flex items-center gap-4">
          <div className={clsx('w-14 h-14 rounded-2xl flex items-center justify-center shadow-sm',
            isPositive ? 'bg-red-100' : 'bg-emerald-100')}>
            {isPositive
              ? <XCircle className="w-8 h-8 text-red-600" />
              : <CheckCircle className="w-8 h-8 text-emerald-600" />}
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-0.5">Prediction Result</p>
            <h2 className={clsx('text-2xl font-bold', isPositive ? 'text-red-700' : 'text-emerald-700')}>{label}</h2>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => navigate(`/counterfactual?disease=${disease}`)}
            className="btn-secondary flex items-center gap-1.5 text-sm">
            <Wand2 className="w-3.5 h-3.5" /> What-If
          </button>
          <button onClick={onReset} className="btn-secondary flex items-center gap-1.5 text-sm">
            <RotateCcw className="w-3.5 h-3.5" /> New
          </button>
        </div>
      </div>

      {/* Risk badge */}
      {risk.level && (
        <div className={clsx(
          'mb-5 flex items-start gap-3 p-3.5 rounded-xl border',
          RISK_STYLES[risk.level] ?? 'bg-slate-50 border-slate-200 text-slate-700'
        )}>
          <div className="flex items-center gap-2 mt-0.5 flex-shrink-0">
            <span className={clsx('w-2.5 h-2.5 rounded-full', RISK_DOT[risk.level] ?? 'bg-slate-400')} />
            <span className="text-sm font-bold">{risk.level} Risk</span>
            <span className="text-sm opacity-70">({risk.pct?.toFixed(1)}%)</span>
          </div>
          <p className="text-sm opacity-80">{risk.action}</p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-5">
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <p className="text-xs text-slate-500 mb-1">Confidence</p>
          <p className="text-2xl font-bold text-slate-900">{confidence}%</p>
          <div className="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div className={clsx('h-full rounded-full transition-all', isPositive ? 'bg-red-500' : 'bg-emerald-500')}
              style={{ width: `${confidence}%` }} />
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <p className="text-xs text-slate-500 mb-1">Model</p>
          <p className="text-sm font-bold text-slate-900 capitalize">
            {result.model_used?.replace(/_/g, ' ')}
          </p>
        </div>
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <p className="text-xs text-slate-500 mb-1">Probabilities</p>
          {Object.entries(result.probability ?? {}).map(([lbl, p]) => (
            <div key={lbl} className="flex justify-between text-xs">
              <span className="text-slate-500 truncate max-w-[60%]">{lbl.split(' ')[0]}</span>
              <span className="font-semibold text-slate-800">{(p * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* SHAP */}
      {shapData.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-5">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-amber-500" />
            <h3 className="font-bold text-slate-900 text-sm">SHAP Feature Impact</h3>
          </div>
          <ResponsiveContainer width="100%" height={Math.max(160, shapData.length * 36)}>
            <BarChart data={shapData} layout="vertical" margin={{ top:0, right:20, left:110, bottom:0 }}>
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={105} />
              <Tooltip formatter={(v, _, p) => [`${v > 0 ? '+' : ''}${v.toFixed(4)}`, p.payload.direction]}
                contentStyle={{ borderRadius: 10, fontSize: 12 }} />
              <Bar dataKey="value" radius={[0,4,4,0]}>
                {shapData.map((e, i) => (
                  <Cell key={i} fill={e.value > 0 ? '#ef4444' : '#10b981'} fillOpacity={0.8} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="text-[11px] text-slate-400 mt-2">🔴 Red increases risk · 🟢 Green decreases risk</p>
        </div>
      )}

      {/* Patient PDF */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-bold text-slate-900">Clinical Report PDF</p>
          <button onClick={() => setShowPdf(v => !v)}
            className="btn-secondary flex items-center gap-1.5 text-sm">
            <Download className="w-3.5 h-3.5" /> Export PDF
          </button>
        </div>
        {showPdf && (
          <div className="mt-3 flex gap-2">
            <input value={patientName} onChange={e => setPatientName(e.target.value)}
              placeholder="Patient name (optional)" className="input-field flex-1" />
            <button onClick={() => pdfMut.mutate()} disabled={pdfMut.isPending}
              className="btn-primary flex items-center gap-2 text-sm flex-shrink-0">
              {pdfMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              Generate
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
