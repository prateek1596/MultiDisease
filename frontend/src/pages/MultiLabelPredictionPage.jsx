import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Activity, AlertTriangle, CheckCircle, TrendingUp, Layers, Info } from 'lucide-react'
import clsx from 'clsx'
import { analyticsAPI } from '../api/client'

const RISK_COLORS = {
  'Low': 'bg-green-100 text-green-800 border-green-200',
  'Elevated': 'bg-yellow-100 text-yellow-800 border-yellow-200',
  'Moderate': 'bg-orange-100 text-orange-800 border-orange-200',
  'High': 'bg-red-100 text-red-800 border-red-200',
  'Critical': 'bg-red-200 text-red-900 border-red-300',
}

const DISEASE_INFO = {
  heart: { emoji: '🫀', label: 'Heart Disease', color: 'red' },
  diabetes: { emoji: '🩸', label: 'Diabetes', color: 'amber' },
  kidney: { emoji: '🫘', label: 'Kidney Disease', color: 'emerald' },
}

const DEFAULT_PATIENT = {
  age: 55,
  sex: 1,
  cp: 2,
  trestbps: 140,
  chol: 240,
  fbs: 1,
  restecg: 1,
  thalach: 150,
  exang: 0,
  oldpeak: 1.5,
  slope: 1,
  ca: 0,
  thal: 2,
  glucose: 120,
  blood_pressure: 140,
  skin_thickness: 25,
  insulin: 80,
  bmi: 28.5,
  diabetes_pedigree: 0.5,
  pregnancies: 2,
  bgr: 120,
  bu: 45,
  sc: 1.2,
  sod: 140,
  pot: 4.5,
  hemo: 14,
  pcv: 42,
  wc: 7000,
  rc: 5,
  htn: 1,
  dm: 1,
  cad: 0,
  appet: 1,
  pe: 0,
  ane: 0,
  sg: 1.02,
  al: 1,
  su: 0
}

export default function MultiLabelPredictionPage() {
  const [patientData, setPatientData] = useState(DEFAULT_PATIENT)
  const [results, setResults] = useState(null)

  // Fetch comorbidity matrix
  const { data: comorbidityMatrix } = useQuery({
    queryKey: ['comorbidityMatrix'],
    queryFn: () => analyticsAPI.getComorbidityMatrix().then(r => r.data?.data),
  })

  // Multi-label prediction mutation
  const predictMutation = useMutation({
    mutationFn: (data) => analyticsAPI.predictMultiLabel(data).then(r => r.data?.data),
    onSuccess: (data) => setResults(data),
  })

  const handlePredict = () => {
    predictMutation.mutate({ patient_data: patientData })
  }

  const updateField = (field, value) => {
    setPatientData(prev => ({ ...prev, [field]: parseFloat(value) || value }))
  }

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <Layers className="w-8 h-8 text-purple-600" />
          Multi-Label Disease Prediction
        </h1>
        <p className="text-slate-500 mt-1">
          Predict risk for all diseases simultaneously with comorbidity analysis
        </p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Patient Data Input */}
        <div className="card p-5">
          <h2 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
            📋 Patient Data
          </h2>
          
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 max-h-96 overflow-y-auto pr-2">
            {Object.entries(patientData).map(([key, value]) => (
              <div key={key} className="space-y-1">
                <label className="text-xs font-medium text-slate-600 capitalize">
                  {key.replace(/_/g, ' ')}
                </label>
                <input
                  type="number"
                  value={value}
                  onChange={(e) => updateField(key, e.target.value)}
                  className="w-full px-2 py-1.5 text-sm border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                />
              </div>
            ))}
          </div>

          <button
            onClick={handlePredict}
            disabled={predictMutation.isPending}
            className="mt-4 w-full py-3 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
          >
            {predictMutation.isPending ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Activity className="w-5 h-5" />
                Predict All Diseases
              </>
            )}
          </button>
        </div>

        {/* Comorbidity Matrix */}
        <div className="card p-5">
          <h2 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
            🔗 Comorbidity Correlation Matrix
          </h2>
          
          {comorbidityMatrix ? (
            <div>
              <div className="grid grid-cols-4 gap-1 text-sm">
                <div></div>
                {comorbidityMatrix.diseases?.map(d => (
                  <div key={d} className="text-center font-medium text-slate-600 capitalize">
                    {DISEASE_INFO[d]?.emoji} {d.slice(0, 5)}
                  </div>
                ))}
                {comorbidityMatrix.diseases?.map((d1, i) => (
                  <>
                    <div key={`row-${d1}`} className="font-medium text-slate-600 capitalize flex items-center">
                      {DISEASE_INFO[d1]?.emoji} {d1}
                    </div>
                    {comorbidityMatrix.correlations?.[i]?.map((corr, j) => (
                      <div
                        key={`${d1}-${j}`}
                        className={clsx(
                          'text-center py-2 rounded font-mono text-sm',
                          corr >= 0.7 ? 'bg-red-100 text-red-800' :
                          corr >= 0.5 ? 'bg-orange-100 text-orange-800' :
                          corr >= 0.3 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-green-100 text-green-800'
                        )}
                      >
                        {corr.toFixed(2)}
                      </div>
                    ))}
                  </>
                ))}
              </div>
              
              <div className="mt-4 space-y-2">
                <h3 className="text-sm font-semibold text-slate-700">Risk Factor Relationships:</h3>
                {Object.entries(comorbidityMatrix.risk_factors || {}).map(([key, info]) => (
                  <div key={key} className="text-xs text-slate-600 bg-slate-50 p-2 rounded">
                    <span className="font-medium capitalize">{key.replace(/_/g, ' ')}</span>: {info.description}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500">
              Loading comorbidity data...
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      {results && (
        <div className="space-y-6">
          {/* Overall Risk */}
          <div className={clsx(
            'card p-5 border-2',
            RISK_COLORS[results.overall_risk] || 'bg-slate-100'
          )}>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold">Overall Risk Assessment</h2>
                <p className="text-sm mt-1">{results.summary}</p>
              </div>
              <div className={clsx(
                'px-4 py-2 rounded-full font-bold text-lg',
                results.overall_risk === 'Critical' ? 'bg-red-600 text-white' :
                results.overall_risk === 'High' ? 'bg-red-500 text-white' :
                results.overall_risk === 'Moderate' ? 'bg-orange-500 text-white' :
                results.overall_risk === 'Elevated' ? 'bg-yellow-500 text-white' :
                'bg-green-500 text-white'
              )}>
                {results.overall_risk}
              </div>
            </div>
          </div>

          {/* Individual Disease Predictions */}
          <div className="grid md:grid-cols-3 gap-4">
            {Object.entries(results.predictions || {}).map(([disease, prediction]) => {
              const prob = results.probabilities?.[disease]
              const info = DISEASE_INFO[disease]
              
              return (
                <div key={disease} className={clsx(
                  'card p-5 border-l-4',
                  prediction ? 'border-l-red-500' : 'border-l-green-500'
                )}>
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-3xl">{info?.emoji}</span>
                    <div>
                      <h3 className="font-bold text-slate-900">{info?.label}</h3>
                      <span className={clsx(
                        'text-sm font-medium px-2 py-0.5 rounded-full',
                        prediction ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                      )}>
                        {prediction ? 'Elevated Risk' : 'Low Risk'}
                      </span>
                    </div>
                  </div>
                  
                  {prob !== null && (
                    <div className="mt-3">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-slate-600">Risk Probability</span>
                        <span className="font-mono font-bold">{(prob * 100).toFixed(1)}%</span>
                      </div>
                      <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className={clsx(
                            'h-full rounded-full transition-all duration-500',
                            prob >= 0.7 ? 'bg-red-500' :
                            prob >= 0.4 ? 'bg-orange-500' :
                            'bg-green-500'
                          )}
                          style={{ width: `${prob * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Comorbidity Analysis */}
          {results.comorbidity_analysis && (
            <div className="card p-5">
              <h2 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-purple-600" />
                Comorbidity Risk Analysis
              </h2>

              {/* Interaction Warnings */}
              {results.comorbidity_analysis.interaction_warnings?.length > 0 && (
                <div className="mb-4 space-y-2">
                  {results.comorbidity_analysis.interaction_warnings.map((warning, i) => (
                    <div key={i} className="flex items-center gap-2 bg-amber-50 text-amber-800 p-3 rounded-lg">
                      <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                      <span>{warning}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Pairwise Risks */}
              <div className="grid sm:grid-cols-3 gap-4">
                {Object.entries(results.comorbidity_analysis.pairwise_risks || {}).map(([pair, data]) => (
                  <div key={pair} className="bg-slate-50 rounded-lg p-4">
                    <h4 className="font-medium text-slate-700 capitalize mb-2">
                      {pair.replace(/_/g, ' + ')}
                    </h4>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span className="text-slate-600">Base Joint Prob:</span>
                        <span className="font-mono">{(data.base_probability * 100).toFixed(1)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-600">Adjusted Risk:</span>
                        <span className="font-mono font-bold text-orange-600">
                          {(data.adjusted_risk * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-500">Risk Multiplier:</span>
                        <span className="text-purple-600">{data.multiplier}x</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Info Card */}
      <div className="card p-5 bg-purple-50 border-purple-200">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-purple-800">About Multi-Label Prediction</h3>
            <p className="text-sm text-purple-700 mt-1">
              This feature predicts risk for all three diseases (heart, diabetes, kidney) simultaneously
              and analyzes potential comorbidities. Comorbidity risk multipliers are based on established
              medical literature showing how these conditions often co-occur and influence each other.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
