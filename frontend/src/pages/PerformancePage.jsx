import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar, CartesianGrid
} from 'recharts'
import { modelsAPI, reportAPI } from '../api/client'
import { Download, BarChart3, Loader2, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const METRIC_COLORS = {
  accuracy:  '#3b82f6',
  precision: '#8b5cf6',
  recall:    '#ec4899',
  f1_score:  '#f59e0b',
  roc_auc:   '#10b981',
}

const TABS = ['heart', 'diabetes', 'kidney']
const TAB_LABELS = { heart: '🫀 Heart', diabetes: '🩸 Diabetes', kidney: '🫘 Kidney' }

export default function PerformancePage() {
  const [activeTab, setActiveTab] = useState('heart')

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['performance'],
    queryFn: () => modelsAPI.performance().then((r) => r.data),
    retry: false,
  })

  const handleDownload = async () => {
    const toastId = toast.loading('Generating PDF report…')
    try {
      const res = await reportAPI.download()
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = 'mdps_report.pdf'
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Report downloaded!', { id: toastId })
    } catch {
      toast.error('Report generation failed', { id: toastId })
    }
  }

  const buildChartData = (diseaseMetrics) => {
    if (!diseaseMetrics) return []
    return Object.entries(diseaseMetrics).map(([model, m]) => ({
      model: model.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      accuracy:  +(m.accuracy  * 100).toFixed(2),
      precision: +(m.precision * 100).toFixed(2),
      recall:    +(m.recall    * 100).toFixed(2),
      f1_score:  +(m.f1_score  * 100).toFixed(2),
      roc_auc:   +(m.roc_auc   * 100).toFixed(2),
    }))
  }

  const buildRadarData = (diseaseMetrics) => {
    if (!diseaseMetrics) return []
    const metrics = ['accuracy', 'precision', 'recall', 'f1_score', 'roc_auc']
    return metrics.map((metric) => {
      const row = { metric: metric.replace('_', ' ').toUpperCase() }
      Object.entries(diseaseMetrics).forEach(([model, m]) => {
        const short = model.replace('logistic_regression', 'LR')
          .replace('random_forest', 'RF')
          .replace('xgboost', 'XGB')
          .replace('lightgbm', 'LGBM')
          .replace('stacking', 'Stack')
          .replace('svm', 'SVM')
        row[short] = +(m[metric] * 100).toFixed(2)
      })
      return row
    })
  }

  const chartData  = buildChartData(data?.[activeTab])
  const radarData  = buildRadarData(data?.[activeTab])
  const modelNames = data?.[activeTab] ? Object.keys(data[activeTab]).map(m =>
    m.replace('logistic_regression','LR').replace('random_forest','RF')
     .replace('xgboost','XGB').replace('lightgbm','LGBM')
     .replace('stacking','Stack').replace('svm','SVM')
  ) : []
  const RADAR_COLORS = ['#3b82f6','#8b5cf6','#ec4899','#f59e0b','#10b981','#ef4444']

  if (isLoading) return (
    <div className="flex items-center justify-center h-64 gap-3 text-slate-500">
      <Loader2 className="w-6 h-6 animate-spin" />
      Loading performance data…
    </div>
  )

  if (isError || !data) return (
    <div className="card p-10 text-center">
      <BarChart3 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
      <h3 className="font-bold text-slate-700 text-lg">No Performance Data</h3>
      <p className="text-slate-500 text-sm mt-1 mb-4">
        Models need to be trained first. Go to the Train page (admin only).
      </p>
      <button onClick={() => refetch()} className="btn-secondary flex items-center gap-2 mx-auto">
        <RefreshCw className="w-4 h-4" />Retry
      </button>
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Model Performance</h1>
          <p className="text-slate-500 mt-1">Compare all 6 models across all 3 diseases</p>
        </div>
        <button onClick={handleDownload} className="btn-primary flex items-center gap-2">
          <Download className="w-4 h-4" /> Download PDF Report
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={clsx(
              'px-4 py-2.5 text-sm font-semibold border-b-2 -mb-px transition-colors',
              activeTab === tab
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            )}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {/* Metrics table */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="font-bold text-slate-900">Metrics Comparison Table</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase">
              <tr>
                {['Model','Accuracy','Precision','Recall','F1-Score','ROC-AUC','Best?'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {Object.entries(data[activeTab] ?? {}).map(([model, m]) => (
                <tr key={model} className={clsx('hover:bg-slate-50', m.is_best && 'bg-amber-50/60')}>
                  <td className="px-4 py-3 font-medium text-slate-800 capitalize">
                    {model.replace(/_/g, ' ')}
                    {m.is_best && <span className="ml-2 badge badge-yellow">⭐ Best</span>}
                  </td>
                  {['accuracy','precision','recall','f1_score','roc_auc'].map((metric) => (
                    <td key={metric} className="px-4 py-3">
                      <span className={clsx(
                        'font-mono font-semibold text-sm',
                        m[metric] >= 0.9 ? 'text-emerald-600' :
                        m[metric] >= 0.75 ? 'text-brand-600' : 'text-slate-600'
                      )}>
                        {(m[metric] * 100).toFixed(2)}%
                      </span>
                    </td>
                  ))}
                  <td className="px-4 py-3">
                    {m.is_best && <span className="text-amber-500">★</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Bar chart */}
        <div className="card p-5">
          <h3 className="font-bold text-slate-900 mb-4">Metrics Comparison (Bar)</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} margin={{ top: 5, right: 5, left: -15, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="model" tick={{ fontSize: 10 }} angle={-35} textAnchor="end" interval={0} />
              <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} unit="%" />
              <Tooltip formatter={(v) => `${v}%`} contentStyle={{ borderRadius: 10, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11, paddingTop: 16 }} />
              {Object.entries(METRIC_COLORS).map(([key, color]) => (
                <Bar key={key} dataKey={key} fill={color} name={key.replace('_', ' ')} radius={[3,3,0,0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Radar chart */}
        <div className="card p-5">
          <h3 className="font-bold text-slate-900 mb-4">Model Radar Comparison</h3>
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#e2e8f0" />
              <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10 }} />
              {modelNames.map((model, i) => (
                <Radar
                  key={model}
                  name={model}
                  dataKey={model}
                  stroke={RADAR_COLORS[i % RADAR_COLORS.length]}
                  fill={RADAR_COLORS[i % RADAR_COLORS.length]}
                  fillOpacity={0.1}
                />
              ))}
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => `${v}%`} contentStyle={{ borderRadius: 10, fontSize: 12 }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
