import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Activity, ChevronDown, Loader2, AlertCircle } from 'lucide-react'
import { predictAPI, analyticsAPI } from '../api/client'
import { DISEASES, MODEL_OPTIONS } from '../utils/diseaseConfig'
import PredictionResult from '../components/Prediction/PredictionResult'
import OutlierAlerts from '../components/Prediction/OutlierAlerts'
import clsx from 'clsx'
import { getApiErrorMessage } from '../utils/apiError'

const colorBorder = {
  heart:    'border-red-400 bg-red-50 text-red-700',
  diabetes: 'border-yellow-400 bg-yellow-50 text-yellow-700',
  kidney:   'border-emerald-400 bg-emerald-50 text-emerald-700',
}

export default function PredictPage() {
  const [searchParams] = useSearchParams()
  const [selectedDisease, setSelectedDisease] = useState(searchParams.get('disease') || 'heart')
  const [selectedModel, setSelectedModel] = useState('best')
  const [result, setResult] = useState(null)
  const [outlierAlerts, setOutlierAlerts] = useState([])
  const [limeExplanation, setLimeExplanation] = useState(null)

  const { register, handleSubmit, reset, formState: { errors } } = useForm()
  const disease = DISEASES[selectedDisease]

  useEffect(() => {
    reset()
    setResult(null)
    setOutlierAlerts([])
    setLimeExplanation(null)
  }, [selectedDisease, reset])

  const mutation = useMutation({
    mutationFn: async (data) => {
      // Check for outliers first
      try {
        const outlierResult = await analyticsAPI.checkOutliers(selectedDisease, data)
        setOutlierAlerts(outlierResult.data.alerts || [])
      } catch (e) {
        console.warn('Outlier check failed:', e)
      }

      // Run prediction
      const predResult = await predictAPI.predict(selectedDisease, {
        disease: selectedDisease,
        model_name: selectedModel,
        input_data: data,
        explain: true,
      })

      // Get LIME explanation
      try {
        const limeResult = await analyticsAPI.explainWithLime(selectedDisease, data, selectedModel)
        setLimeExplanation(limeResult.data)
      } catch (e) {
        console.warn('LIME explanation failed:', e)
      }

      return predResult.data
    },
    onSuccess: (data) => {
      setResult(data)
      toast.success('Prediction complete!')
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    onError: (err) => {
      const msg = getApiErrorMessage(err, 'Prediction failed. Are models trained?')
      toast.error(msg)
    },
  })

  const onSubmit = (data) => {
    // Convert string values to numbers
    const numeric = {}
    Object.entries(data).forEach(([k, v]) => {
      numeric[k] = v === '' ? 0 : parseFloat(v)
    })
    mutation.mutate(numeric)
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Disease Prediction</h1>
        <p className="text-slate-500 mt-1">Fill in the patient's clinical data to get an AI-powered prediction</p>
      </div>

      {/* Disease selector */}
      <div className="card p-5">
        <p className="text-sm font-semibold text-slate-600 mb-3">Select Disease</p>
        <div className="flex gap-3 flex-wrap">
          {Object.entries(DISEASES).map(([key, d]) => (
            <button
              key={key}
              onClick={() => setSelectedDisease(key)}
              className={clsx(
                'flex items-center gap-2.5 px-4 py-2.5 rounded-xl border-2 text-sm font-semibold transition-all duration-150',
                selectedDisease === key
                  ? colorBorder[key]
                  : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
              )}
            >
              <span className="text-lg">{d.emoji}</span>
              {d.label}
            </button>
          ))}
        </div>
      </div>

      {result && (
        <PredictionResult 
          result={result} 
          disease={selectedDisease} 
          onReset={() => { setResult(null); setOutlierAlerts([]); setLimeExplanation(null) }}
          limeExplanation={limeExplanation}
        />
      )}

      {/* Outlier Alerts */}
      {outlierAlerts.length > 0 && !result && (
        <div className="card p-5">
          <OutlierAlerts alerts={outlierAlerts} />
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        {/* Model selector */}
        <div className="card p-5">
          <p className="text-sm font-semibold text-slate-600 mb-3">Model Selection</p>
          <div className="relative max-w-xs">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="input-field appearance-none pr-10 cursor-pointer"
            >
              {MODEL_OPTIONS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>
        </div>

        {/* Fields */}
        <div className="card p-6">
          <h2 className="font-bold text-slate-900 text-lg mb-1 flex items-center gap-2">
            <span className="text-2xl">{disease.emoji}</span>
            {disease.label} — Clinical Features
          </h2>
          <p className="text-sm text-slate-500 mb-5">{disease.description}</p>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {disease.fields.map((field) => (
              <div key={field.name}>
                <label className="block text-xs font-semibold text-slate-600 mb-1.5">
                  {field.label}
                  {field.unit && (
                    <span className="ml-1 font-normal text-slate-400">({field.unit})</span>
                  )}
                </label>

                {field.type === 'select' ? (
                  <div className="relative">
                    <select
                      {...register(field.name, { required: true })}
                      className="input-field appearance-none pr-8 cursor-pointer"
                    >
                      {field.options.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                  </div>
                ) : (
                  <input
                    type="number"
                    step={field.step ?? 1}
                    min={field.min}
                    max={field.max}
                    placeholder={field.placeholder}
                    {...register(field.name, {
                      required: 'Required',
                      min: { value: field.min, message: `Min ${field.min}` },
                      max: { value: field.max, message: `Max ${field.max}` },
                    })}
                    className={clsx('input-field', errors[field.name] && 'border-red-400 focus:border-red-400 focus:ring-red-200')}
                  />
                )}

                {errors[field.name] && (
                  <p className="text-xs text-red-500 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {errors[field.name].message || 'Required'}
                  </p>
                )}
                {field.hint && !errors[field.name] && (
                  <p className="text-[11px] text-slate-400 mt-1">{field.hint}</p>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="btn-primary flex items-center gap-2"
          >
            {mutation.isPending ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Predicting…</>
            ) : (
              <><Activity className="w-4 h-4" /> Run Prediction</>
            )}
          </button>
          <button type="button" onClick={() => { reset(); setResult(null); setOutlierAlerts([]); setLimeExplanation(null) }} className="btn-secondary">
            Clear Form
          </button>
        </div>
      </form>
    </div>
  )
}
