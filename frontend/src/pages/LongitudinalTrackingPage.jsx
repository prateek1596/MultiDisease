import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, AreaChart, Area
} from 'recharts'
import { 
  TrendingUp, Calendar, AlertTriangle, CheckCircle, 
  Plus, History, Activity, Users, Search, Trash2, Info
} from 'lucide-react'
import clsx from 'clsx'
import { analyticsAPI } from '../api/client'

const DISEASE_COLORS = {
  heart: '#ef4444',
  diabetes: '#f59e0b',
  kidney: '#10b981',
}

const DISEASE_INFO = {
  heart: { emoji: '🫀', label: 'Heart' },
  diabetes: { emoji: '🩸', label: 'Diabetes' },
  kidney: { emoji: '🫘', label: 'Kidney' },
}

export default function LongitudinalTrackingPage() {
  const [selectedPatientId, setSelectedPatientId] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [showRecordModal, setShowRecordModal] = useState(false)

  // Fetch all patients
  const { data: patients, refetch: refetchPatients } = useQuery({
    queryKey: ['patients'],
    queryFn: () => analyticsAPI.listPatients().then(r => r.data?.data || []),
  })

  // Fetch selected patient history
  const { data: patientHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['patientHistory', selectedPatientId],
    queryFn: () => analyticsAPI.getPatientHistory(selectedPatientId).then(r => r.data?.data),
    enabled: !!selectedPatientId,
  })

  // Fetch timeline data
  const { data: timelineData } = useQuery({
    queryKey: ['timeline', selectedPatientId],
    queryFn: () => analyticsAPI.getTimelineData(selectedPatientId).then(r => r.data?.data),
    enabled: !!selectedPatientId,
  })

  // Generate demo data
  const generateDemoMutation = useMutation({
    mutationFn: (patientId) => analyticsAPI.generateDemoPatient(patientId).then(r => r.data),
    onSuccess: () => {
      refetchPatients()
      setSelectedPatientId('demo-patient-001')
    },
  })

  // Filter patients by search
  const filteredPatients = patients?.filter(p => 
    p.patient_id?.toLowerCase().includes(searchTerm.toLowerCase())
  ) || []

  // Prepare chart data
  const chartData = timelineData?.data?.map(point => ({
    date: point.date,
    ...Object.fromEntries(
      Object.keys(DISEASE_COLORS).map(d => [d, point[d] ? (point[d] * 100).toFixed(1) : null])
    )
  })) || []

  const trendAnalysis = patientHistory?.trend_analysis

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <TrendingUp className="w-8 h-8 text-blue-600" />
          Longitudinal Patient Tracking
        </h1>
        <p className="text-slate-500 mt-1">
          Track patient risk scores over time and identify trends
        </p>
      </div>

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Patient List */}
        <div className="card p-4 lg:col-span-1">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-slate-900 flex items-center gap-2">
              <Users className="w-4 h-4" />
              Patients
            </h2>
            <button
              onClick={() => generateDemoMutation.mutate('demo-patient-001')}
              className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded hover:bg-blue-200"
              disabled={generateDemoMutation.isPending}
            >
              {generateDemoMutation.isPending ? '...' : '+ Demo'}
            </button>
          </div>

          <div className="relative mb-3">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search patients..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="space-y-2 max-h-96 overflow-y-auto">
            {filteredPatients.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-4">
                No patients found. Click "+ Demo" to generate sample data.
              </p>
            ) : (
              filteredPatients.map(patient => (
                <button
                  key={patient.patient_id}
                  onClick={() => setSelectedPatientId(patient.patient_id)}
                  className={clsx(
                    'w-full text-left p-3 rounded-lg text-sm transition-all',
                    selectedPatientId === patient.patient_id
                      ? 'bg-blue-100 border-2 border-blue-500'
                      : 'bg-slate-50 hover:bg-slate-100 border-2 border-transparent'
                  )}
                >
                  <div className="font-medium text-slate-900">{patient.patient_id}</div>
                  <div className="text-xs text-slate-500 mt-1">
                    {patient.total_visits} visit{patient.total_visits !== 1 ? 's' : ''}
                  </div>
                  <div className="text-xs text-slate-400">
                    Last: {patient.last_visit?.slice(0, 10)}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3 space-y-6">
          {!selectedPatientId ? (
            <div className="card p-10 text-center">
              <History className="w-12 h-12 mx-auto text-slate-300 mb-4" />
              <h3 className="text-lg font-semibold text-slate-600">Select a Patient</h3>
              <p className="text-sm text-slate-500 mt-1">
                Choose a patient from the list to view their longitudinal data
              </p>
            </div>
          ) : historyLoading ? (
            <div className="card p-10 text-center">
              <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-slate-500 mt-3">Loading patient data...</p>
            </div>
          ) : (
            <>
              {/* Patient Header */}
              <div className="card p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-slate-900">{selectedPatientId}</h2>
                    <p className="text-sm text-slate-500">
                      {patientHistory?.total_visits || 0} visits recorded
                    </p>
                  </div>
                  <button
                    onClick={() => setShowRecordModal(true)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Record Visit
                  </button>
                </div>
              </div>

              {/* Trend Analysis Alerts */}
              {trendAnalysis?.alerts?.length > 0 && (
                <div className="space-y-2">
                  {trendAnalysis.alerts.map((alert, i) => (
                    <div
                      key={i}
                      className={clsx(
                        'card p-4 flex items-center gap-3 border-l-4',
                        alert.severity === 'high'
                          ? 'border-red-500 bg-red-50'
                          : 'border-amber-500 bg-amber-50'
                      )}
                    >
                      <AlertTriangle className={clsx(
                        'w-5 h-5 flex-shrink-0',
                        alert.severity === 'high' ? 'text-red-600' : 'text-amber-600'
                      )} />
                      <span className={alert.severity === 'high' ? 'text-red-800' : 'text-amber-800'}>
                        {alert.message}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Timeline Chart */}
              <div className="card p-5">
                <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-blue-600" />
                  Risk Score Timeline
                </h3>

                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <defs>
                        {Object.entries(DISEASE_COLORS).map(([disease, color]) => (
                          <linearGradient key={disease} id={`color${disease}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={color} stopOpacity={0.3}/>
                            <stop offset="95%" stopColor={color} stopOpacity={0}/>
                          </linearGradient>
                        ))}
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis domain={[0, 100]} tickFormatter={v => `${v}%`} />
                      <Tooltip formatter={(v) => `${v}%`} />
                      <Legend />
                      {Object.entries(DISEASE_COLORS).map(([disease, color]) => (
                        <Area
                          key={disease}
                          type="monotone"
                          dataKey={disease}
                          stroke={color}
                          fillOpacity={1}
                          fill={`url(#color${disease})`}
                          name={`${DISEASE_INFO[disease].emoji} ${DISEASE_INFO[disease].label}`}
                          strokeWidth={2}
                          connectNulls
                        />
                      ))}
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-center py-8 text-slate-500">
                    No timeline data available
                  </div>
                )}
              </div>

              {/* Trend Summary */}
              {trendAnalysis?.trends && (
                <div className="card p-5">
                  <h3 className="font-bold text-slate-900 mb-4">📈 Trend Analysis</h3>
                  
                  <div className="grid md:grid-cols-3 gap-4">
                    {Object.entries(trendAnalysis.trends).map(([disease, trend]) => (
                      <div key={disease} className="bg-slate-50 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xl">{DISEASE_INFO[disease]?.emoji}</span>
                          <span className="font-semibold capitalize">{disease}</span>
                        </div>
                        
                        <div className={clsx(
                          'text-lg font-bold flex items-center gap-2',
                          trend.direction === 'increasing' ? 'text-red-600' :
                          trend.direction === 'decreasing' ? 'text-green-600' :
                          'text-slate-600'
                        )}>
                          {trend.direction === 'increasing' ? '↗️' :
                           trend.direction === 'decreasing' ? '↘️' : '→'}
                          {trend.direction?.charAt(0).toUpperCase() + trend.direction?.slice(1)}
                        </div>

                        <div className="mt-2 space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span className="text-slate-600">First:</span>
                            <span className="font-mono">{((trend.first_value || 0) * 100).toFixed(1)}%</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-600">Latest:</span>
                            <span className="font-mono">{((trend.last_value || 0) * 100).toFixed(1)}%</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-600">Change:</span>
                            <span className={clsx(
                              'font-mono',
                              trend.percent_change > 0 ? 'text-red-600' :
                              trend.percent_change < 0 ? 'text-green-600' :
                              'text-slate-600'
                            )}>
                              {trend.percent_change > 0 ? '+' : ''}{trend.percent_change?.toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {trendAnalysis.summary && (
                    <div className="mt-4 bg-blue-50 rounded-lg p-4">
                      <span className="font-medium text-blue-800">Summary: </span>
                      <span className="text-blue-700">{trendAnalysis.summary}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Visit History */}
              <div className="card p-5">
                <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-blue-600" />
                  Visit History
                </h3>

                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {patientHistory?.visits?.slice().reverse().map((visit, i) => (
                    <div key={visit.visit_id || i} className="bg-slate-50 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-slate-700">
                          {visit.timestamp?.slice(0, 10)}
                        </span>
                        <span className="text-xs text-slate-500 font-mono">
                          {visit.visit_id?.slice(0, 8)}
                        </span>
                      </div>
                      
                      <div className="flex gap-3">
                        {Object.entries(visit.predictions?.probabilities || {}).map(([disease, prob]) => (
                          <div key={disease} className="flex items-center gap-1">
                            <span>{DISEASE_INFO[disease]?.emoji}</span>
                            <span className={clsx(
                              'text-sm font-mono',
                              prob >= 0.5 ? 'text-red-600' : 'text-green-600'
                            )}>
                              {(prob * 100).toFixed(0)}%
                            </span>
                          </div>
                        ))}
                      </div>

                      {visit.notes && (
                        <p className="text-xs text-slate-500 mt-2">{visit.notes}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Info */}
      <div className="card p-5 bg-blue-50 border-blue-200">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-blue-800">About Longitudinal Tracking</h3>
            <p className="text-sm text-blue-700 mt-1">
              Longitudinal tracking monitors a patient's risk scores over multiple visits to identify
              trends and detect significant changes. This helps clinicians understand disease progression
              and evaluate the effectiveness of interventions over time.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
