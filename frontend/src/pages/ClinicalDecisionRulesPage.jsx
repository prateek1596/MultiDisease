import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar
} from 'recharts'
import { Scale, CheckCircle, AlertTriangle, ClipboardList, Activity, Info } from 'lucide-react'
import clsx from 'clsx'
import { analyticsAPI } from '../api/client'

const DISEASES = [
  { key: 'heart', label: 'Heart Disease', emoji: '🫀', color: '#ef4444' },
  { key: 'diabetes', label: 'Diabetes', emoji: '🩸', color: '#f59e0b' },
  { key: 'kidney', label: 'Kidney Disease', emoji: '🫘', color: '#10b981' },
]

const DEFAULT_PATIENT = {
  age: 55, sex: 1, trestbps: 140, chol: 240, fbs: 1, hdl: 45,
  glucose: 120, bmi: 28.5, blood_pressure: 140, diabetes_pedigree: 0.5,
  sc: 1.2, al: 1, pregnancies: 2, smoker: 0
}

export default function ClinicalDecisionRulesPage() {
  const [selectedDisease, setSelectedDisease] = useState('heart')
  const [patientData, setPatientData] = useState(DEFAULT_PATIENT)
  const [mlPrediction, setMlPrediction] = useState(0.65)
  const [results, setResults] = useState(null)

  // Fetch available rules
  const { data: availableRules } = useQuery({
    queryKey: ['availableRules'],
    queryFn: () => analyticsAPI.getAvailableRules().then(r => r.data?.data),
  })

  // Clinical rules comparison mutation
  const compareMutation = useMutation({
    mutationFn: (data) => analyticsAPI.compareWithClinicalRules(data).then(r => r.data?.data),
    onSuccess: (data) => setResults(data),
  })

  const handleCompare = () => {
    compareMutation.mutate({
      disease: selectedDisease,
      patient_data: patientData,
      ml_prediction: mlPrediction
    })
  }

  // Prepare comparison chart data
  const comparisonData = results?.clinical_scores?.map(score => ({
    name: score.name.replace(/\s+/g, '\n').split('\n')[0],
    probability: score.probability * 100,
    ml: mlPrediction * 100
  })) || []

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <Scale className="w-8 h-8 text-emerald-600" />
          Clinical Decision Rules
        </h1>
        <p className="text-slate-500 mt-1">
          Compare AI predictions with established clinical guidelines (Framingham, WHO, ADA, KDIGO)
        </p>
      </div>

      {/* Available Rules Overview */}
      <div className="card p-5">
        <h2 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
          <ClipboardList className="w-5 h-5 text-emerald-600" />
          Available Clinical Decision Rules
        </h2>
        
        <div className="grid md:grid-cols-3 gap-4">
          {DISEASES.map(d => (
            <div key={d.key} className={clsx(
              'p-4 rounded-lg border-2 transition-all cursor-pointer',
              selectedDisease === d.key
                ? 'border-emerald-500 bg-emerald-50'
                : 'border-slate-200 hover:border-slate-300'
            )} onClick={() => setSelectedDisease(d.key)}>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">{d.emoji}</span>
                <span className="font-semibold">{d.label}</span>
              </div>
              <ul className="text-sm text-slate-600 space-y-1">
                {(availableRules?.[d.key] || []).map((rule, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <CheckCircle className="w-3 h-3 text-emerald-500" />
                    {rule}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Input Section */}
      <div className="card p-5">
        <h2 className="font-bold text-slate-900 mb-4">Patient Data & ML Prediction</h2>
        
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Patient Data */}
          <div>
            <label className="block text-sm font-semibold text-slate-600 mb-2">Patient Features</label>
            <div className="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto pr-2">
              {Object.entries(patientData).map(([key, value]) => (
                <div key={key}>
                  <label className="text-xs text-slate-500 capitalize">{key.replace(/_/g, ' ')}</label>
                  <input
                    type="number"
                    value={value}
                    onChange={(e) => setPatientData(prev => ({ ...prev, [key]: parseFloat(e.target.value) }))}
                    className="w-full px-2 py-1 text-sm border rounded focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* ML Prediction */}
          <div>
            <label className="block text-sm font-semibold text-slate-600 mb-2">
              ML Model Prediction: {(mlPrediction * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={mlPrediction}
              onChange={(e) => setMlPrediction(parseFloat(e.target.value))}
              className="w-full h-3 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
            />
            <div className="flex justify-between text-xs text-slate-400 mt-1">
              <span>0% (Low Risk)</span>
              <span>50%</span>
              <span>100% (High Risk)</span>
            </div>

            <div className="mt-4 bg-slate-50 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Current ML Risk Level:</span>
                <span className={clsx(
                  'px-3 py-1 rounded-full text-sm font-medium',
                  mlPrediction >= 0.7 ? 'bg-red-100 text-red-700' :
                  mlPrediction >= 0.4 ? 'bg-yellow-100 text-yellow-700' :
                  'bg-green-100 text-green-700'
                )}>
                  {mlPrediction >= 0.7 ? 'High' : mlPrediction >= 0.4 ? 'Moderate' : 'Low'}
                </span>
              </div>
            </div>

            <button
              onClick={handleCompare}
              disabled={compareMutation.isPending}
              className="mt-4 w-full py-3 bg-emerald-600 text-white font-semibold rounded-lg hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {compareMutation.isPending ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Comparing...
                </>
              ) : (
                <>
                  <Scale className="w-5 h-5" />
                  Compare with Clinical Rules
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      {results && (
        <div className="space-y-6">
          {/* Agreement Analysis */}
          <div className={clsx(
            'card p-5 border-2',
            results.agreement_analysis?.status === 'strong_agreement'
              ? 'border-green-300 bg-green-50'
              : results.agreement_analysis?.status === 'significant_disagreement'
              ? 'border-red-300 bg-red-50'
              : 'border-yellow-300 bg-yellow-50'
          )}>
            <div className="flex items-start gap-4">
              {results.agreement_analysis?.status === 'strong_agreement' ? (
                <CheckCircle className="w-8 h-8 text-green-600 flex-shrink-0" />
              ) : results.agreement_analysis?.status === 'significant_disagreement' ? (
                <AlertTriangle className="w-8 h-8 text-red-600 flex-shrink-0" />
              ) : (
                <Scale className="w-8 h-8 text-yellow-600 flex-shrink-0" />
              )}
              <div>
                <h3 className="font-bold text-lg capitalize">
                  {results.agreement_analysis?.status?.replace(/_/g, ' ')}
                </h3>
                <p className="text-sm mt-1">{results.agreement_analysis?.message}</p>
                <div className="mt-2 text-sm">
                  <span className="font-medium">Agreement Rate: </span>
                  <span className="font-mono">{((results.agreement_analysis?.agreement_rate || 0) * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Comparison Chart */}
          <div className="card p-5">
            <h3 className="font-bold text-slate-900 mb-4">📊 ML vs Clinical Rules Comparison</h3>
            
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={comparisonData} layout="vertical" margin={{ left: 20, right: 30 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} />
                <YAxis type="category" dataKey="name" width={100} />
                <Tooltip formatter={(v) => `${v.toFixed(1)}%`} />
                <Legend />
                <Bar dataKey="probability" fill="#10b981" name="Clinical Score" />
                <Bar dataKey="ml" fill="#6366f1" name="ML Prediction" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Clinical Scores Detail */}
          <div className="grid md:grid-cols-2 gap-4">
            {results.clinical_scores?.map((score, i) => (
              <div key={i} className="card p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h4 className="font-bold text-slate-900">{score.name}</h4>
                    <span className={clsx(
                      'text-xs px-2 py-0.5 rounded-full',
                      score.risk_category?.toLowerCase().includes('high') || score.risk_category?.toLowerCase().includes('very')
                        ? 'bg-red-100 text-red-700'
                        : score.risk_category?.toLowerCase().includes('moderate')
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-green-100 text-green-700'
                    )}>
                      {score.risk_category}
                    </span>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-slate-900">
                      {score.score}{score.unit === 'points' ? '' : score.unit}
                    </div>
                    {score.max_score && (
                      <div className="text-xs text-slate-500">/ {score.max_score}</div>
                    )}
                  </div>
                </div>

                <div className="bg-slate-50 rounded-lg p-3 mb-3">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-slate-600">Risk Probability</span>
                    <span className="font-mono font-bold">{((score.probability || 0) * 100).toFixed(1)}%</span>
                  </div>
                  <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className={clsx(
                        'h-full rounded-full',
                        (score.probability || 0) >= 0.5 ? 'bg-red-500' :
                        (score.probability || 0) >= 0.2 ? 'bg-yellow-500' :
                        'bg-green-500'
                      )}
                      style={{ width: `${(score.probability || 0) * 100}%` }}
                    />
                  </div>
                </div>

                <p className="text-sm text-slate-600 mb-2">{score.interpretation}</p>
                
                <div className="flex flex-wrap gap-1">
                  {score.factors_used?.map((factor, j) => (
                    <span key={j} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded capitalize">
                      {factor}
                    </span>
                  ))}
                </div>

                <div className="mt-3 pt-3 border-t text-xs text-slate-500">
                  Source: {score.source}
                </div>
              </div>
            ))}
          </div>

          {/* Recommendation */}
          {results.recommendation && (
            <div className="card p-5 bg-emerald-50 border-emerald-200">
              <h3 className="font-bold text-emerald-800 mb-2 flex items-center gap-2">
                <Activity className="w-5 h-5" />
                Combined Recommendation
              </h3>
              <p className="text-emerald-700">{results.recommendation}</p>
            </div>
          )}
        </div>
      )}

      {/* Info */}
      <div className="card p-5 bg-emerald-50 border-emerald-200">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-emerald-800">About Clinical Decision Rules</h3>
            <p className="text-sm text-emerald-700 mt-1">
              Clinical decision rules are evidence-based scoring systems validated in medical research.
              Comparing ML predictions with these established guidelines provides clinical validation
              and helps identify cases where additional review may be warranted.
            </p>
            <ul className="mt-2 text-sm text-emerald-600 space-y-1">
              <li><strong>Framingham:</strong> 10-year cardiovascular disease risk (D'Agostino et al., 2008)</li>
              <li><strong>WHO CVD:</strong> WHO cardiovascular risk charts (2019 update)</li>
              <li><strong>ADA Risk Test:</strong> American Diabetes Association Type 2 screening</li>
              <li><strong>KDIGO:</strong> Kidney Disease: Improving Global Outcomes CKD staging</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
