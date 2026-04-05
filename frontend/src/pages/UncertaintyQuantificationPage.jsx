import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, BarChart, Bar, ReferenceLine
} from 'recharts'
import { ShieldCheck, AlertCircle, Target, TrendingUp, Activity, Info } from 'lucide-react'
import clsx from 'clsx'
import { analyticsAPI } from '../api/client'

const DISEASES = [
  { key: 'heart', label: 'Heart Disease', emoji: '🫀' },
  { key: 'diabetes', label: 'Diabetes', emoji: '🩸' },
  { key: 'kidney', label: 'Kidney Disease', emoji: '🫘' },
]

const DEFAULT_PATIENT = {
  age: 55, sex: 1, trestbps: 140, chol: 240, fbs: 1,
  glucose: 120, bmi: 28.5, sc: 1.2
}

export default function UncertaintyQuantificationPage() {
  const [selectedDisease, setSelectedDisease] = useState('heart')
  const [patientData, setPatientData] = useState(DEFAULT_PATIENT)
  const [results, setResults] = useState(null)

  // Fetch calibration curve
  const { data: calibration } = useQuery({
    queryKey: ['calibration', selectedDisease],
    queryFn: () => analyticsAPI.getCalibration(selectedDisease).then(r => r.data?.data),
  })

  // Uncertainty quantification mutation
  const quantifyMutation = useMutation({
    mutationFn: (data) => analyticsAPI.quantifyUncertainty(data).then(r => r.data?.data),
    onSuccess: (data) => setResults(data),
  })

  const handleQuantify = () => {
    quantifyMutation.mutate({
      disease: selectedDisease,
      patient_data: patientData,
      n_simulations: 100
    })
  }

  // Prepare calibration chart data
  const calibrationData = calibration ? 
    calibration.mean_predicted?.map((pred, i) => ({
      predicted: pred,
      actual: calibration.fraction_positive?.[i] || pred,
      perfect: pred
    })) : []

  // Prepare confidence interval chart data
  const ciData = results?.confidence_intervals ? 
    Object.entries(results.confidence_intervals).map(([level, data]) => ({
      level,
      lower: data.lower,
      upper: data.upper,
      width: data.width,
      point: results.point_estimate?.probability || 0
    })) : []

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <ShieldCheck className="w-8 h-8 text-indigo-600" />
          Uncertainty Quantification
        </h1>
        <p className="text-slate-500 mt-1">
          Confidence intervals, ensemble variance, and prediction stability analysis
        </p>
      </div>

      {/* Disease Selection & Input */}
      <div className="card p-5">
        <div className="flex flex-wrap gap-6 items-end">
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

          <div className="flex-1 grid grid-cols-4 gap-2">
            {Object.entries(patientData).slice(0, 4).map(([key, value]) => (
              <div key={key}>
                <label className="text-xs text-slate-500 capitalize">{key}</label>
                <input
                  type="number"
                  value={value}
                  onChange={(e) => setPatientData(prev => ({ ...prev, [key]: parseFloat(e.target.value) }))}
                  className="w-full px-2 py-1 text-sm border rounded focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            ))}
          </div>

          <button
            onClick={handleQuantify}
            disabled={quantifyMutation.isPending}
            className="px-6 py-2 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
          >
            {quantifyMutation.isPending ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Activity className="w-4 h-4" />
                Quantify Uncertainty
              </>
            )}
          </button>
        </div>
      </div>

      {/* Results */}
      {results && (
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Point Estimate & Stability */}
          <div className="card p-5">
            <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-indigo-600" />
              Prediction Analysis
            </h3>

            {/* Point Estimate */}
            <div className="bg-slate-50 rounded-lg p-4 mb-4">
              <div className="flex justify-between items-center">
                <div>
                  <span className="text-sm text-slate-600">Point Estimate</span>
                  <div className="text-3xl font-bold text-slate-900">
                    {((results.point_estimate?.probability || 0) * 100).toFixed(1)}%
                  </div>
                </div>
                <div className={clsx(
                  'px-3 py-1 rounded-full text-sm font-medium',
                  results.point_estimate?.prediction
                    ? 'bg-red-100 text-red-700'
                    : 'bg-green-100 text-green-700'
                )}>
                  {results.point_estimate?.prediction ? 'High Risk' : 'Low Risk'}
                </div>
              </div>
            </div>

            {/* Prediction Stability */}
            {results.prediction_stability && (
              <div className={clsx(
                'rounded-lg p-4 border-l-4',
                results.prediction_stability.color === 'green' ? 'bg-green-50 border-green-500' :
                results.prediction_stability.color === 'blue' ? 'bg-blue-50 border-blue-500' :
                results.prediction_stability.color === 'yellow' ? 'bg-yellow-50 border-yellow-500' :
                'bg-red-50 border-red-500'
              )}>
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold">{results.prediction_stability.category}</span>
                  <span className="text-sm font-mono">
                    σ = {results.prediction_stability.std_deviation?.toFixed(4)}
                  </span>
                </div>
                <p className="text-sm opacity-80">{results.prediction_stability.description}</p>
              </div>
            )}

            {/* Ensemble Variance */}
            {results.ensemble_variance !== null && (
              <div className="mt-4 bg-purple-50 rounded-lg p-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-purple-800">Ensemble Variance</span>
                  <span className="font-mono text-purple-900">
                    {results.ensemble_variance?.toFixed(6)}
                  </span>
                </div>
                <div className="mt-2 h-2 bg-purple-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-500 rounded-full"
                    style={{ width: `${Math.min(results.ensemble_variance * 1000, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-purple-600 mt-1">
                  Lower variance indicates more consistent predictions across models
                </p>
              </div>
            )}

            {/* Recommendation */}
            {results.recommendation && (
              <div className="mt-4 bg-indigo-50 rounded-lg p-4 border border-indigo-200">
                <span className="text-sm font-semibold text-indigo-800">💡 Recommendation</span>
                <p className="text-sm text-indigo-700 mt-1">{results.recommendation}</p>
              </div>
            )}
          </div>

          {/* Confidence Intervals */}
          <div className="card p-5">
            <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-indigo-600" />
              Confidence Intervals
            </h3>

            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={ciData} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 1]} tickFormatter={v => `${(v*100).toFixed(0)}%`} />
                <YAxis type="category" dataKey="level" />
                <Tooltip formatter={(v) => `${(v*100).toFixed(2)}%`} />
                <Bar dataKey="lower" stackId="ci" fill="#c7d2fe" name="Lower Bound" />
                <Bar dataKey="width" stackId="ci" fill="#6366f1" name="Interval Width" />
                <ReferenceLine x={results.point_estimate?.probability || 0} stroke="#ef4444" strokeDasharray="3 3" />
              </BarChart>
            </ResponsiveContainer>

            <div className="mt-4 space-y-2">
              {Object.entries(results.confidence_intervals || {}).map(([level, data]) => (
                <div key={level} className="flex justify-between items-center bg-slate-50 p-2 rounded">
                  <span className="font-medium text-slate-700">{level} CI</span>
                  <span className="font-mono text-sm">
                    [{(data.lower * 100).toFixed(1)}%, {(data.upper * 100).toFixed(1)}%]
                  </span>
                  <span className="text-xs text-slate-500">
                    width: {(data.width * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Uncertainty Sources */}
          {results.uncertainty_sources?.length > 0 && (
            <div className="card p-5">
              <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-amber-600" />
                Uncertainty Sources
              </h3>
              
              <div className="space-y-3">
                {results.uncertainty_sources.map((source, i) => (
                  <div key={i} className={clsx(
                    'p-3 rounded-lg border-l-4',
                    source.severity === 'high' ? 'bg-red-50 border-red-500' :
                    source.severity === 'moderate' ? 'bg-amber-50 border-amber-500' :
                    'bg-blue-50 border-blue-500'
                  )}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={clsx(
                        'text-xs font-medium px-2 py-0.5 rounded-full',
                        source.severity === 'high' ? 'bg-red-200 text-red-800' :
                        source.severity === 'moderate' ? 'bg-amber-200 text-amber-800' :
                        'bg-blue-200 text-blue-800'
                      )}>
                        {source.severity}
                      </span>
                      <span className="text-sm font-medium capitalize">
                        {source.type?.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-sm opacity-80">{source.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Calibration Curve */}
          <div className="card p-5">
            <h3 className="font-bold text-slate-900 mb-4">📊 Model Calibration Curve</h3>
            
            {calibrationData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={calibrationData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="predicted" 
                      label={{ value: 'Mean Predicted', position: 'bottom', offset: 0 }}
                      tickFormatter={v => `${(v*100).toFixed(0)}%`}
                    />
                    <YAxis 
                      label={{ value: 'Fraction Positive', angle: -90, position: 'insideLeft' }}
                      tickFormatter={v => `${(v*100).toFixed(0)}%`}
                    />
                    <Tooltip formatter={(v) => `${(v*100).toFixed(1)}%`} />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="perfect" 
                      stroke="#94a3b8" 
                      strokeDasharray="5 5"
                      dot={false}
                      name="Perfect Calibration"
                    />
                    <Line 
                      type="monotone" 
                      dataKey="actual" 
                      stroke="#6366f1" 
                      strokeWidth={2}
                      name="Model"
                    />
                  </LineChart>
                </ResponsiveContainer>

                <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                  <div className="bg-slate-50 p-3 rounded-lg">
                    <span className="text-slate-600">Calibration Error</span>
                    <div className="font-mono font-bold">
                      {(calibration?.calibration_error * 100)?.toFixed(2)}%
                    </div>
                  </div>
                  <div className="bg-slate-50 p-3 rounded-lg">
                    <span className="text-slate-600">Brier Score</span>
                    <div className="font-mono font-bold">
                      {calibration?.brier_score?.toFixed(4)}
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-slate-500">
                Loading calibration data...
              </div>
            )}
          </div>
        </div>
      )}

      {/* Info */}
      <div className="card p-5 bg-indigo-50 border-indigo-200">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-indigo-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-indigo-800">About Uncertainty Quantification</h3>
            <p className="text-sm text-indigo-700 mt-1">
              Uncertainty quantification provides reliability estimates for predictions. It uses ensemble
              methods to calculate prediction variance and bootstrap resampling for confidence intervals.
              Well-calibrated models have calibration curves close to the diagonal (perfect calibration).
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
