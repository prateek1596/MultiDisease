import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { 
  Upload, FileSpreadsheet, Download, AlertTriangle, 
  CheckCircle, XCircle, Loader2, FileDown, BarChart3
} from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { api } from '../api/client'

const DISEASES = [
  { key: 'heart', label: 'Heart Disease', emoji: '🫀' },
  { key: 'diabetes', label: 'Diabetes', emoji: '🩸' },
  { key: 'kidney', label: 'Kidney Disease', emoji: '🫘' },
]

export default function BatchPredictionPage() {
  const [selectedDisease, setSelectedDisease] = useState('heart')
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [results, setResults] = useState(null)

  const uploadMutation = useMutation({
    mutationFn: async (formData) => {
      const response = await api.post(`/predict/batch/${selectedDisease}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return response.data
    },
    onSuccess: (data) => {
      setResults(data)
      toast.success(`Processed ${data.summary.total_records} records!`)
    },
    onError: (err) => {
      const msg = err.response?.data?.detail || 'Batch prediction failed'
      toast.error(msg)
    },
  })

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile?.name.endsWith('.csv')) {
      setFile(droppedFile)
      setResults(null)
    } else {
      toast.error('Please drop a CSV file')
    }
  }, [])

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setResults(null)
    }
  }

  const handleUpload = () => {
    if (!file) return
    
    const formData = new FormData()
    formData.append('file', file)
    formData.append('model_name', 'best')
    formData.append('include_outliers', 'true')
    
    uploadMutation.mutate(formData)
  }

  const downloadTemplate = async () => {
    try {
      const response = await api.get(`/predict/batch/template/${selectedDisease}`, {
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `${selectedDisease}_template.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (e) {
      toast.error('Failed to download template')
    }
  }

  const downloadResults = async () => {
    if (!file) return
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('model_name', 'best')
      formData.append('include_outliers', 'true')
      
      const response = await api.post(`/predict/batch/${selectedDisease}/download`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `${selectedDisease}_predictions.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      
      toast.success('Results downloaded!')
    } catch (e) {
      toast.error('Failed to download results')
    }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <FileSpreadsheet className="w-8 h-8 text-indigo-600" />
          Batch CSV Prediction
        </h1>
        <p className="text-slate-500 mt-1">
          Upload a CSV file with multiple patient records for bulk predictions
        </p>
      </div>

      {/* Disease Selection */}
      <div className="card p-5">
        <label className="block text-sm font-semibold text-slate-600 mb-3">
          Select Disease Type
        </label>
        <div className="flex gap-3 flex-wrap">
          {DISEASES.map(d => (
            <button
              key={d.key}
              onClick={() => { setSelectedDisease(d.key); setResults(null) }}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                selectedDisease === d.key
                  ? 'bg-indigo-100 text-indigo-700 ring-2 ring-indigo-500'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              )}
            >
              <span>{d.emoji}</span>
              {d.label}
            </button>
          ))}
        </div>
      </div>

      {/* File Upload Area */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-slate-900">Upload CSV File</h3>
          <button
            onClick={downloadTemplate}
            className="btn-secondary flex items-center gap-2 text-sm"
          >
            <FileDown className="w-4 h-4" />
            Download Template
          </button>
        </div>

        <div
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          className={clsx(
            'border-2 border-dashed rounded-xl p-10 text-center transition-all',
            dragOver
              ? 'border-indigo-400 bg-indigo-50'
              : 'border-slate-200 hover:border-slate-300'
          )}
        >
          <Upload className={clsx(
            'w-12 h-12 mx-auto mb-4',
            dragOver ? 'text-indigo-500' : 'text-slate-400'
          )} />
          
          {file ? (
            <div>
              <p className="font-medium text-slate-700">{file.name}</p>
              <p className="text-sm text-slate-500 mt-1">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
          ) : (
            <div>
              <p className="text-slate-600 font-medium">
                Drag and drop your CSV file here
              </p>
              <p className="text-sm text-slate-400 mt-1">or</p>
            </div>
          )}
          
          <label className="mt-4 inline-block">
            <input
              type="file"
              accept=".csv"
              onChange={handleFileSelect}
              className="hidden"
            />
            <span className="btn-secondary cursor-pointer">
              Browse Files
            </span>
          </label>
        </div>

        {file && (
          <div className="mt-4 flex gap-3">
            <button
              onClick={handleUpload}
              disabled={uploadMutation.isPending}
              className="btn-primary flex items-center gap-2"
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Run Predictions
                </>
              )}
            </button>
            <button
              onClick={() => { setFile(null); setResults(null) }}
              className="btn-secondary"
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {/* Results */}
      {results && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <SummaryCard
              label="Total Records"
              value={results.summary.total_records}
              icon={FileSpreadsheet}
              color="indigo"
            />
            <SummaryCard
              label="Positive Predictions"
              value={results.summary.positive_predictions}
              subtext={`${(results.summary.positive_rate * 100).toFixed(1)}%`}
              icon={AlertTriangle}
              color="red"
            />
            <SummaryCard
              label="Negative Predictions"
              value={results.summary.negative_predictions}
              icon={CheckCircle}
              color="emerald"
            />
            <SummaryCard
              label="Avg Confidence"
              value={`${(results.summary.average_confidence * 100).toFixed(1)}%`}
              icon={BarChart3}
              color="blue"
            />
          </div>

          {/* Outlier Warning */}
          {results.summary.records_with_outliers > 0 && (
            <div className="card p-4 bg-amber-50 border-amber-200">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
                <div>
                  <p className="font-medium text-amber-800">
                    {results.summary.records_with_outliers} records have outlier values
                  </p>
                  <p className="text-sm text-amber-600">
                    {(results.summary.outlier_rate * 100).toFixed(1)}% of records have values outside the training data distribution
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Download Results */}
          <div className="card p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900">Download Results</h3>
                <p className="text-sm text-slate-500">
                  Download CSV with original data plus prediction columns
                </p>
              </div>
              <button
                onClick={downloadResults}
                className="btn-primary flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download CSV
              </button>
            </div>
          </div>

          {/* Results Preview */}
          <div className="card p-5">
            <h3 className="font-bold text-slate-900 mb-4">
              Results Preview (First 10 records)
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-2 px-3 font-semibold text-slate-600">Row</th>
                    <th className="text-left py-2 px-3 font-semibold text-slate-600">Prediction</th>
                    <th className="text-left py-2 px-3 font-semibold text-slate-600">Confidence</th>
                    <th className="text-left py-2 px-3 font-semibold text-slate-600">Outliers</th>
                    <th className="text-left py-2 px-3 font-semibold text-slate-600">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {results.predictions.slice(0, 10).map((pred, idx) => (
                    <tr key={idx} className="border-b border-slate-100">
                      <td className="py-2 px-3 text-slate-600">{pred.row_index + 1}</td>
                      <td className="py-2 px-3">
                        {pred.status === 'success' ? (
                          <span className={clsx(
                            'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                            pred.prediction === 1
                              ? 'bg-red-100 text-red-700'
                              : 'bg-emerald-100 text-emerald-700'
                          )}>
                            {pred.prediction === 1 ? (
                              <><XCircle className="w-3 h-3" /> Positive</>
                            ) : (
                              <><CheckCircle className="w-3 h-3" /> Negative</>
                            )}
                          </span>
                        ) : (
                          <span className="text-slate-400">-</span>
                        )}
                      </td>
                      <td className="py-2 px-3">
                        {pred.status === 'success' ? (
                          <span className="font-medium">
                            {(pred.confidence * 100).toFixed(1)}%
                          </span>
                        ) : '-'}
                      </td>
                      <td className="py-2 px-3">
                        {pred.has_outliers ? (
                          <span className="text-amber-600 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" />
                            {pred.outlier_count}
                          </span>
                        ) : (
                          <span className="text-emerald-600">✓</span>
                        )}
                      </td>
                      <td className="py-2 px-3">
                        {pred.status === 'success' ? (
                          <span className="text-emerald-600">Success</span>
                        ) : (
                          <span className="text-red-600">Error</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function SummaryCard({ label, value, subtext, icon: Icon, color }) {
  const colorClasses = {
    indigo: 'bg-indigo-100 text-indigo-600',
    red: 'bg-red-100 text-red-600',
    emerald: 'bg-emerald-100 text-emerald-600',
    blue: 'bg-blue-100 text-blue-600',
  }
  
  return (
    <div className="card p-4">
      <div className="flex items-center gap-3">
        <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center', colorClasses[color])}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-bold text-slate-900">{value}</p>
          <p className="text-xs text-slate-500">
            {label}
            {subtext && <span className="ml-1 text-slate-400">({subtext})</span>}
          </p>
        </div>
      </div>
    </div>
  )
}
