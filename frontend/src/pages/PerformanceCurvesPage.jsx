import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, 
  ResponsiveContainer, Area, AreaChart
} from 'recharts'
import { Activity, Target, Layers, Sliders, AlertCircle } from 'lucide-react'
import clsx from 'clsx'
import { analyticsAPI } from '../api/client'

const DISEASES = [
  { key: 'heart', label: 'Heart Disease', emoji: '🫀', color: '#ef4444' },
  { key: 'diabetes', label: 'Diabetes', emoji: '🩸', color: '#f59e0b' },
  { key: 'kidney', label: 'Kidney Disease', emoji: '🫘', color: '#10b981' },
]

const MODEL_COLORS = {
  logistic_regression: '#3b82f6',
  random_forest: '#10b981',
  svm: '#8b5cf6',
  xgboost: '#f59e0b',
  lightgbm: '#06b6d4',
  stacking: '#ec4899',
}

// Demo data for when models aren't trained
const DEMO_ROC_DATA = Array.from({ length: 50 }, (_, i) => {
  const fpr = i / 49
  // Simulate a good ROC curve (above diagonal)
  const tpr = Math.min(1, fpr + 0.3 + Math.random() * 0.2 * (1 - fpr))
  return { fpr, tpr: Math.min(1, tpr) }
}).sort((a, b) => a.fpr - b.fpr)

const DEMO_PR_DATA = Array.from({ length: 50 }, (_, i) => {
  const recall = i / 49
  // Simulate a PR curve
  const precision = Math.max(0.3, 1 - recall * 0.5 + Math.random() * 0.1)
  return { recall, precision: Math.min(1, precision) }
}).sort((a, b) => a.recall - b.recall)

const DEMO_THRESHOLD_METRICS = {
  tn: 45, fp: 5, fn: 8, tp: 42,
  accuracy: 0.87, precision: 0.89, recall: 0.84, specificity: 0.90, f1: 0.86
}

export default function PerformanceCurvesPage() {
  const [selectedDisease, setSelectedDisease] = useState('heart')
  const [selectedModel, setSelectedModel] = useState('best')
  const [threshold, setThreshold] = useState(0.5)
  const [showComparison, setShowComparison] = useState(false)

  // Fetch curves for selected model
  const { data: curves, isLoading: curvesLoading, error: curvesError } = useQuery({
    queryKey: ['curves', selectedDisease, selectedModel],
    queryFn: () => analyticsAPI.getCurves(selectedDisease, selectedModel).then(r => r.data),
    enabled: !showComparison,
    retry: 1,
  })

  // Fetch comparison data
  const { data: comparison, isLoading: comparisonLoading, error: comparisonError } = useQuery({
    queryKey: ['curvesComparison', selectedDisease],
    queryFn: () => analyticsAPI.compareCurves(selectedDisease).then(r => r.data),
    enabled: showComparison,
    retry: 1,
  })

  // Fetch threshold metrics
  const { data: thresholdMetrics, error: thresholdError } = useQuery({
    queryKey: ['thresholdMetrics', selectedDisease, selectedModel, threshold],
    queryFn: () => analyticsAPI.getThresholdMetrics(selectedDisease, threshold, selectedModel).then(r => r.data),
    retry: 1,
  })

  const isLoading = curvesLoading || comparisonLoading
  const hasError = curvesError || comparisonError
  const usingDemo = hasError || (!curves && !isLoading && !showComparison)

  // Prepare ROC curve data
  const rocData = useMemo(() => {
    if (showComparison && comparison?.models) {
      const allData = []
      Object.entries(comparison.models).forEach(([modelName, modelData]) => {
        if (modelData.roc_curve) {
          modelData.roc_curve.fpr.forEach((fpr, idx) => {
            if (!allData[idx]) allData[idx] = { fpr }
            allData[idx][modelName] = modelData.roc_curve.tpr[idx]
          })
        }
      })
      return allData.length > 0 ? allData : DEMO_ROC_DATA
    }
    
    if (curves?.roc_curve?.fpr?.length > 0) {
      return curves.roc_curve.fpr.map((fpr, idx) => ({
        fpr,
        tpr: curves.roc_curve.tpr[idx],
      }))
    }
    return DEMO_ROC_DATA
  }, [curves, comparison, showComparison])

  // Prepare PR curve data
  const prData = useMemo(() => {
    if (curves?.pr_curve?.recall?.length > 0) {
      return curves.pr_curve.recall.map((recall, idx) => ({
        recall,
        precision: curves.pr_curve.precision[idx],
      }))
    }
    return DEMO_PR_DATA
  }, [curves])

  const displayThresholdMetrics = thresholdMetrics || DEMO_THRESHOLD_METRICS
  const displayAuc = curves?.roc_auc ?? 0.85

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <Activity className="w-8 h-8 text-indigo-600" />
          Interactive Performance Curves
        </h1>
        <p className="text-slate-500 mt-1">
          Explore ROC curves, precision-recall curves, and confusion matrices at different thresholds
        </p>
      </div>

      {/* Disease & Model Selection */}
      <div className="card p-5 flex flex-wrap gap-6">
        {/* Disease selector */}
        <div>
          <label className="block text-sm font-semibold text-slate-600 mb-2">Disease</label>
          <div className="flex gap-2">
            {DISEASES.map(d => (
              <button
                key={d.key}
                onClick={() => setSelectedDisease(d.key)}
                className={clsx(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-all',
                  selectedDisease === d.key
                    ? 'bg-indigo-100 text-indigo-700 ring-2 ring-indigo-500'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                )}
              >
                {d.emoji} {d.label}
              </button>
            ))}
          </div>
        </div>

        {/* Comparison toggle */}
        <div>
          <label className="block text-sm font-semibold text-slate-600 mb-2">View Mode</label>
          <div className="flex gap-2">
            <button
              onClick={() => setShowComparison(false)}
              className={clsx(
                'px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2',
                !showComparison
                  ? 'bg-indigo-100 text-indigo-700 ring-2 ring-indigo-500'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              )}
            >
              <Target className="w-4 h-4" />
              Single Model
            </button>
            <button
              onClick={() => setShowComparison(true)}
              className={clsx(
                'px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2',
                showComparison
                  ? 'bg-indigo-100 text-indigo-700 ring-2 ring-indigo-500'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              )}
            >
              <Layers className="w-4 h-4" />
              Compare All
            </button>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="card p-10 text-center">
          <div className="animate-spin w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto" />
          <p className="text-slate-500 mt-3">Loading performance data...</p>
        </div>
      ) : (
        <>
          {/* Demo mode notice */}
          {usingDemo && (
            <div className="card p-4 bg-amber-50 border-amber-200 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
              <div>
                <p className="text-amber-800 font-medium">Showing Demo Data</p>
                <p className="text-amber-700 text-sm">
                  Models haven't been trained yet. Train models first to see actual performance curves.
                </p>
              </div>
            </div>
          )}
          
          <div className="grid lg:grid-cols-2 gap-6">
            {/* ROC Curve */}
            <div className="card p-5">
              <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
                📈 ROC Curve
                <span className="text-sm font-normal text-slate-500">
                  AUC = {displayAuc.toFixed(4)}
                </span>
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={rocData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="fpr" 
                    label={{ value: 'False Positive Rate', position: 'bottom', offset: 0 }}
                    domain={[0, 1]}
                    type="number"
                    tickFormatter={v => v.toFixed(1)}
                  />
                  <YAxis 
                    label={{ value: 'True Positive Rate', angle: -90, position: 'insideLeft' }}
                    domain={[0, 1]}
                    tickFormatter={v => v.toFixed(1)}
                  />
                  <Tooltip 
                    formatter={(value, name) => [typeof value === 'number' ? value.toFixed(4) : value, name]}
                    labelFormatter={v => `FPR: ${typeof v === 'number' ? v.toFixed(4) : v}`}
                  />
                  {/* Diagonal reference line (random classifier) */}
                  <Line
                    data={[{fpr: 0, diagonal: 0}, {fpr: 1, diagonal: 1}]}
                    type="linear"
                    dataKey="diagonal"
                    stroke="#94a3b8"
                    strokeDasharray="5 5"
                    strokeWidth={1}
                    dot={false}
                    name="Random"
                    legendType="none"
                  />
                  {showComparison && comparison?.models ? (
                    Object.keys(comparison.models).map(modelName => (
                      <Line
                        key={modelName}
                        type="monotone"
                        dataKey={modelName}
                        stroke={MODEL_COLORS[modelName] || '#6b7280'}
                        strokeWidth={2}
                        dot={false}
                        name={`${modelName} (AUC: ${comparison.models[modelName].roc_auc?.toFixed(3)})`}
                      />
                    ))
                  ) : (
                    <Line
                      type="monotone"
                      dataKey="tpr"
                      stroke="#6366f1"
                      strokeWidth={2}
                      dot={false}
                      name={`ROC Curve (AUC: ${displayAuc.toFixed(3)})`}
                    />
                  )}
                  <Legend />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* PR Curve */}
            <div className="card p-5">
              <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
                📊 Precision-Recall Curve
                <span className="text-sm font-normal text-slate-500">
                  AUC = {(curves?.pr_auc ?? 0.82).toFixed(4)}
                </span>
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={prData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="recall" 
                    label={{ value: 'Recall', position: 'bottom', offset: 0 }}
                    domain={[0, 1]}
                    type="number"
                    tickFormatter={v => v.toFixed(1)}
                  />
                  <YAxis 
                    label={{ value: 'Precision', angle: -90, position: 'insideLeft' }}
                    domain={[0, 1]}
                    tickFormatter={v => v.toFixed(1)}
                  />
                  <Tooltip 
                    formatter={(value) => [typeof value === 'number' ? value.toFixed(4) : value]}
                    labelFormatter={v => `Recall: ${typeof v === 'number' ? v.toFixed(4) : v}`}
                  />
                  <Line
                    type="monotone"
                    dataKey="precision"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                    name="Precision-Recall"
                  />
                  <Legend />
                </LineChart>
              </ResponsiveContainer>
            </div>

          {/* Threshold Slider */}
          <div className="card p-5 lg:col-span-2">
            <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Sliders className="w-5 h-5" />
              Decision Threshold Explorer
            </h3>
            
            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-600 mb-2">
                Threshold: {threshold.toFixed(2)}
              </label>
              <input
                type="range"
                min="0.1"
                max="0.9"
                step="0.05"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
              />
              <div className="flex justify-between text-xs text-slate-400 mt-1">
                <span>0.1 (More Positive)</span>
                <span>0.5 (Balanced)</span>
                <span>0.9 (More Negative)</span>
              </div>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Confusion Matrix */}
              <div className="bg-slate-50 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-slate-700 mb-3">Confusion Matrix</h4>
                <div className="grid grid-cols-2 gap-1 text-center text-sm">
                  <div className="bg-emerald-100 text-emerald-800 p-2 rounded">
                    TN: {displayThresholdMetrics.tn}
                  </div>
                  <div className="bg-red-100 text-red-800 p-2 rounded">
                    FP: {displayThresholdMetrics.fp}
                  </div>
                  <div className="bg-orange-100 text-orange-800 p-2 rounded">
                    FN: {displayThresholdMetrics.fn}
                  </div>
                  <div className="bg-blue-100 text-blue-800 p-2 rounded">
                    TP: {displayThresholdMetrics.tp}
                  </div>
                </div>
              </div>

              {/* Metrics */}
              <div className="bg-slate-50 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-slate-700 mb-3">Classification Metrics</h4>
                <div className="space-y-2 text-sm">
                  <MetricRow label="Accuracy" value={displayThresholdMetrics.accuracy} />
                  <MetricRow label="Precision" value={displayThresholdMetrics.precision} />
                  <MetricRow label="Recall" value={displayThresholdMetrics.recall} />
                  <MetricRow label="F1 Score" value={displayThresholdMetrics.f1} />
                </div>
              </div>

              {/* Additional Metrics */}
              <div className="bg-slate-50 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-slate-700 mb-3">Additional Metrics</h4>
                <div className="space-y-2 text-sm">
                  <MetricRow label="Specificity" value={displayThresholdMetrics.specificity} />
                  <MetricRow label="NPV" value={displayThresholdMetrics.tn / (displayThresholdMetrics.tn + displayThresholdMetrics.fn) || 0} />
                  <MetricRow label="FPR" value={1 - displayThresholdMetrics.specificity} />
                  <MetricRow label="FNR" value={1 - displayThresholdMetrics.recall} />
                </div>
              </div>

              {/* Interpretation */}
              <div className="bg-indigo-50 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-indigo-700 mb-3">💡 Interpretation</h4>
                <p className="text-xs text-indigo-600 leading-relaxed">
                  {threshold < 0.4 
                    ? "Lower threshold: More cases classified as positive. Higher recall but more false positives. Good when missing positive cases is costly."
                    : threshold > 0.6
                    ? "Higher threshold: Fewer cases classified as positive. Higher precision but may miss positive cases. Good when false alarms are costly."
                    : "Balanced threshold: Trade-off between precision and recall. Suitable for general use cases."}
                </p>
              </div>
            </div>
          </div>
        </div>
        </>
      )}
    </div>
  )
}

function MetricRow({ label, value }) {
  const percentage = (value * 100).toFixed(1)
  return (
    <div className="flex justify-between items-center">
      <span className="text-slate-600">{label}</span>
      <div className="flex items-center gap-2">
        <div className="w-16 h-2 bg-slate-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-indigo-500 rounded-full transition-all duration-300"
            style={{ width: `${Math.min(value * 100, 100)}%` }}
          />
        </div>
        <span className="text-slate-900 font-medium w-12 text-right">{percentage}%</span>
      </div>
    </div>
  )
}
