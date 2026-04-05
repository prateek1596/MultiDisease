import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, 
  ResponsiveContainer, Cell
} from 'recharts'
import { BarChart3, Activity } from 'lucide-react'
import clsx from 'clsx'
import { analyticsAPI } from '../api/client'

const DISEASES = [
  { key: 'heart', label: 'Heart Disease', emoji: '🫀', color: '#ef4444' },
  { key: 'diabetes', label: 'Diabetes', emoji: '🩸', color: '#f59e0b' },
  { key: 'kidney', label: 'Kidney Disease', emoji: '🫘', color: '#10b981' },
]

const DISEASE_COLORS = {
  heart: '#ef4444',
  diabetes: '#f59e0b',
  kidney: '#10b981',
}

export default function FeatureImportancePage() {
  const [selectedDisease, setSelectedDisease] = useState('heart')
  const [showAllDiseases, setShowAllDiseases] = useState(false)

  // Fetch single disease importance
  const { data: importance, isLoading } = useQuery({
    queryKey: ['featureImportance', selectedDisease],
    queryFn: () => analyticsAPI.getFeatureImportance(selectedDisease).then(r => r.data),
    enabled: !showAllDiseases,
  })

  // Fetch all diseases for comparison
  const { data: allImportance, isLoading: allLoading } = useQuery({
    queryKey: ['featureImportanceAll'],
    queryFn: async () => {
      const results = await Promise.all(
        DISEASES.map(d => 
          analyticsAPI.getFeatureImportance(d.key)
            .then(r => ({ disease: d.key, ...r.data }))
            .catch(() => ({ disease: d.key, importance_list: [] }))
        )
      )
      return results
    },
    enabled: showAllDiseases,
  })

  // Prepare chart data
  const chartData = importance?.importance_list?.slice(0, 15).map((item, idx) => ({
    name: formatFeatureName(item.feature),
    fullName: item.feature,
    importance: item.importance,
    fill: getBarColor(idx),
  })) || []

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <BarChart3 className="w-8 h-8 text-indigo-600" />
          Feature Importance Dashboard
        </h1>
        <p className="text-slate-500 mt-1">
          Understand which features have the most influence on disease predictions
        </p>
      </div>

      {/* Controls */}
      <div className="card p-5 flex flex-wrap gap-6 items-end">
        <div>
          <label className="block text-sm font-semibold text-slate-600 mb-2">Disease</label>
          <div className="flex gap-2">
            {DISEASES.map(d => (
              <button
                key={d.key}
                onClick={() => {
                  setSelectedDisease(d.key)
                  setShowAllDiseases(false)
                }}
                className={clsx(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-all',
                  selectedDisease === d.key && !showAllDiseases
                    ? 'bg-indigo-100 text-indigo-700 ring-2 ring-indigo-500'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                )}
              >
                {d.emoji} {d.label}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => setShowAllDiseases(!showAllDiseases)}
          className={clsx(
            'px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2',
            showAllDiseases
              ? 'bg-indigo-100 text-indigo-700 ring-2 ring-indigo-500'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          )}
        >
          <Activity className="w-4 h-4" />
          Compare All Diseases
        </button>
      </div>

      {isLoading || allLoading ? (
        <div className="card p-10 text-center">
          <div className="animate-spin w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto" />
          <p className="text-slate-500 mt-3">Loading feature importance...</p>
        </div>
      ) : showAllDiseases ? (
        // Comparison view
        <div className="grid lg:grid-cols-3 gap-6">
          {allImportance?.map(diseaseData => {
            const d = DISEASES.find(x => x.key === diseaseData.disease)
            const data = diseaseData.importance_list?.slice(0, 10).map((item, idx) => ({
              name: formatFeatureName(item.feature),
              importance: item.importance,
            })) || []

            return (
              <div key={diseaseData.disease} className="card p-5">
                <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
                  {d?.emoji} {d?.label}
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={data} layout="vertical" margin={{ left: 80 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      type="number" 
                      domain={[0, 1]} 
                      tickFormatter={v => `${(v * 100).toFixed(0)}%`}
                    />
                    <YAxis 
                      type="category" 
                      dataKey="name" 
                      tick={{ fontSize: 11 }}
                      width={80}
                    />
                    <Tooltip 
                      formatter={(value) => [`${(value * 100).toFixed(2)}%`, 'Importance']}
                    />
                    <Bar dataKey="importance" fill={DISEASE_COLORS[diseaseData.disease]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )
          })}
        </div>
      ) : (
        // Single disease view
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Chart */}
          <div className="card p-5 lg:col-span-2">
            <h3 className="font-bold text-slate-900 mb-4">
              Top Features for {DISEASES.find(d => d.key === selectedDisease)?.label}
            </h3>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 120 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  type="number" 
                  domain={[0, 'dataMax']} 
                  tickFormatter={v => `${(v * 100).toFixed(0)}%`}
                />
                <YAxis 
                  type="category" 
                  dataKey="name" 
                  tick={{ fontSize: 12 }}
                  width={120}
                />
                <Tooltip 
                  formatter={(value) => [`${(value * 100).toFixed(2)}%`, 'Importance']}
                  labelFormatter={(label) => chartData.find(d => d.name === label)?.fullName}
                />
                <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Feature List */}
          <div className="card p-5">
            <h3 className="font-bold text-slate-900 mb-4">Feature Rankings</h3>
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {importance?.importance_list?.map((item, idx) => (
                <div key={item.feature} className="flex items-center gap-3">
                  <div className={clsx(
                    'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold',
                    idx < 3 ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'
                  )}>
                    {idx + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-700 truncate" title={item.feature}>
                      {formatFeatureName(item.feature)}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                        <div 
                          className="h-full rounded-full transition-all duration-500"
                          style={{ 
                            width: `${item.importance * 100}%`,
                            backgroundColor: getBarColor(idx),
                          }}
                        />
                      </div>
                      <span className="text-xs text-slate-500 w-12 text-right">
                        {(item.importance * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Explanation */}
      <div className="card p-5 bg-indigo-50 border-indigo-100">
        <h3 className="font-bold text-indigo-900 mb-2">📖 Understanding Feature Importance</h3>
        <div className="text-sm text-indigo-700 space-y-2">
          <p>
            <strong>What it shows:</strong> Feature importance measures how much each input variable 
            contributes to the model's predictions. Higher values mean the feature has more influence.
          </p>
          <p>
            <strong>How it's calculated:</strong> For tree-based models (Random Forest, XGBoost), 
            importance is based on how often a feature is used to split data and how much it improves predictions. 
            For linear models, it's based on coefficient magnitudes.
          </p>
          <p>
            <strong>Clinical insight:</strong> Top features often align with known clinical risk factors, 
            validating the model's decision-making process.
          </p>
        </div>
      </div>
    </div>
  )
}

function formatFeatureName(name) {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
    .replace(/Bmi/g, 'BMI')
    .replace(/Ecg/g, 'ECG')
    .replace(/Bp/g, 'BP')
}

function getBarColor(index) {
  const colors = [
    '#6366f1', '#8b5cf6', '#a855f7', '#d946ef', 
    '#ec4899', '#f43f5e', '#ef4444', '#f97316',
    '#f59e0b', '#eab308', '#84cc16', '#22c55e',
    '#10b981', '#14b8a6', '#06b6d4',
  ]
  return colors[index % colors.length]
}
