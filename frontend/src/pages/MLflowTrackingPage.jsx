import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, LineChart, Line
} from 'recharts'
import { 
  Database, GitBranch, Play, CheckCircle, Clock, 
  AlertCircle, Layers, Tag, ArrowRight, Beaker, Info
} from 'lucide-react'
import clsx from 'clsx'
import { analyticsAPI } from '../api/client'

const STAGE_COLORS = {
  staging: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  production: 'bg-green-100 text-green-800 border-green-200',
  archived: 'bg-slate-100 text-slate-600 border-slate-200',
}

const STATUS_COLORS = {
  running: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

export default function MLflowTrackingPage() {
  const [selectedTab, setSelectedTab] = useState('summary')
  const [selectedExperiment, setSelectedExperiment] = useState(null)
  const [selectedModel, setSelectedModel] = useState(null)
  const queryClient = useQueryClient()

  // Fetch summary
  const { data: summary } = useQuery({
    queryKey: ['mlflowSummary'],
    queryFn: () => analyticsAPI.getMlflowSummary().then(r => r.data?.data),
  })

  // Fetch experiments
  const { data: experiments } = useQuery({
    queryKey: ['experiments'],
    queryFn: () => analyticsAPI.listExperiments().then(r => r.data?.data || []),
    enabled: selectedTab === 'experiments',
  })

  // Fetch runs
  const { data: runs } = useQuery({
    queryKey: ['runs', selectedExperiment],
    queryFn: () => analyticsAPI.listRuns(selectedExperiment).then(r => r.data?.data || []),
    enabled: selectedTab === 'experiments' && !!selectedExperiment,
  })

  // Fetch models
  const { data: models } = useQuery({
    queryKey: ['registeredModels'],
    queryFn: () => analyticsAPI.listRegisteredModels().then(r => r.data?.data || []),
    enabled: selectedTab === 'models',
  })

  // Fetch model details
  const { data: modelDetails } = useQuery({
    queryKey: ['modelDetails', selectedModel],
    queryFn: () => analyticsAPI.getModelDetails(selectedModel).then(r => r.data?.data),
    enabled: !!selectedModel,
  })

  // Initialize demo data
  const initDemoMutation = useMutation({
    mutationFn: () => analyticsAPI.initializeMlflowDemo().then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries(['mlflowSummary'])
      queryClient.invalidateQueries(['experiments'])
      queryClient.invalidateQueries(['registeredModels'])
    },
  })

  // Transition stage mutation
  const transitionMutation = useMutation({
    mutationFn: ({ name, version, stage }) => 
      analyticsAPI.transitionModelStage(name, version, stage).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries(['modelDetails', selectedModel])
      queryClient.invalidateQueries(['registeredModels'])
    },
  })

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <Database className="w-8 h-8 text-orange-600" />
            MLflow Model Tracking
          </h1>
          <p className="text-slate-500 mt-1">
            Experiment tracking, model versioning, and registry management
          </p>
        </div>
        
        <button
          onClick={() => initDemoMutation.mutate()}
          disabled={initDemoMutation.isPending}
          className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 flex items-center gap-2"
        >
          {initDemoMutation.isPending ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Initializing...
            </>
          ) : (
            <>
              <Beaker className="w-4 h-4" />
              Initialize Demo Data
            </>
          )}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        {['summary', 'experiments', 'models'].map(tab => (
          <button
            key={tab}
            onClick={() => setSelectedTab(tab)}
            className={clsx(
              'px-4 py-2 font-medium border-b-2 transition-all capitalize',
              selectedTab === tab
                ? 'border-orange-500 text-orange-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Summary Tab */}
      {selectedTab === 'summary' && summary && (
        <div className="space-y-6">
          {/* Stats */}
          <div className="grid sm:grid-cols-4 gap-4">
            <div className="card p-5 text-center">
              <Beaker className="w-8 h-8 mx-auto text-orange-500 mb-2" />
              <div className="text-3xl font-bold text-slate-900">{summary.total_experiments}</div>
              <div className="text-sm text-slate-500">Experiments</div>
            </div>
            <div className="card p-5 text-center">
              <Play className="w-8 h-8 mx-auto text-blue-500 mb-2" />
              <div className="text-3xl font-bold text-slate-900">{summary.total_runs}</div>
              <div className="text-sm text-slate-500">Total Runs</div>
            </div>
            <div className="card p-5 text-center">
              <Layers className="w-8 h-8 mx-auto text-purple-500 mb-2" />
              <div className="text-3xl font-bold text-slate-900">{summary.total_models}</div>
              <div className="text-sm text-slate-500">Registered Models</div>
            </div>
            <div className="card p-5 text-center">
              <CheckCircle className="w-8 h-8 mx-auto text-green-500 mb-2" />
              <div className="text-3xl font-bold text-slate-900">{summary.production_models}</div>
              <div className="text-sm text-slate-500">In Production</div>
            </div>
          </div>

          {/* Run Status */}
          <div className="card p-5">
            <h3 className="font-bold text-slate-900 mb-4">Run Status Distribution</h3>
            <div className="grid sm:grid-cols-3 gap-4">
              {Object.entries(summary.runs_by_status || {}).map(([status, count]) => (
                <div key={status} className={clsx(
                  'p-4 rounded-lg text-center',
                  STATUS_COLORS[status] || 'bg-slate-100'
                )}>
                  <div className="text-2xl font-bold">{count}</div>
                  <div className="text-sm capitalize">{status}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="grid lg:grid-cols-2 gap-6">
            <div className="card p-5">
              <h3 className="font-bold text-slate-900 mb-4">Recent Experiments</h3>
              <div className="space-y-2">
                {(summary.recent_experiments || []).map(exp => (
                  <div key={exp.experiment_id} className="bg-slate-50 rounded-lg p-3">
                    <div className="font-medium text-slate-900">{exp.name}</div>
                    <div className="text-xs text-slate-500">
                      Created: {exp.created_at?.slice(0, 10)}
                    </div>
                  </div>
                ))}
                {summary.recent_experiments?.length === 0 && (
                  <p className="text-slate-500 text-sm">No experiments yet</p>
                )}
              </div>
            </div>

            <div className="card p-5">
              <h3 className="font-bold text-slate-900 mb-4">Recent Models</h3>
              <div className="space-y-2">
                {(summary.recent_models || []).map(model => (
                  <div key={model.name} className="bg-slate-50 rounded-lg p-3">
                    <div className="font-medium text-slate-900">{model.name}</div>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span>v{model.latest_version}</span>
                      <span>•</span>
                      <span>{model.total_versions} version(s)</span>
                    </div>
                  </div>
                ))}
                {summary.recent_models?.length === 0 && (
                  <p className="text-slate-500 text-sm">No models registered</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Experiments Tab */}
      {selectedTab === 'experiments' && (
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Experiments List */}
          <div className="card p-4">
            <h3 className="font-bold text-slate-900 mb-4">Experiments</h3>
            <div className="space-y-2">
              {(experiments || []).map(exp => (
                <button
                  key={exp.experiment_id}
                  onClick={() => setSelectedExperiment(exp.experiment_id)}
                  className={clsx(
                    'w-full text-left p-3 rounded-lg transition-all',
                    selectedExperiment === exp.experiment_id
                      ? 'bg-orange-100 border-2 border-orange-500'
                      : 'bg-slate-50 hover:bg-slate-100 border-2 border-transparent'
                  )}
                >
                  <div className="font-medium text-slate-900">{exp.name}</div>
                  <div className="text-xs text-slate-500 mt-1">{exp.description}</div>
                  <div className="text-xs text-slate-400 mt-1">
                    {exp.runs?.length || 0} runs
                  </div>
                </button>
              ))}
              {experiments?.length === 0 && (
                <p className="text-slate-500 text-sm text-center py-4">
                  No experiments. Click "Initialize Demo Data" to create some.
                </p>
              )}
            </div>
          </div>

          {/* Runs List */}
          <div className="card p-4 lg:col-span-2">
            <h3 className="font-bold text-slate-900 mb-4">
              {selectedExperiment ? 'Runs' : 'Select an experiment'}
            </h3>
            
            {selectedExperiment && runs ? (
              <div className="space-y-3">
                {runs.map(run => (
                  <div key={run.run_id} className="bg-slate-50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{run.run_name}</span>
                        <span className={clsx(
                          'text-xs px-2 py-0.5 rounded-full',
                          STATUS_COLORS[run.status]
                        )}>
                          {run.status}
                        </span>
                      </div>
                      <span className="text-xs text-slate-500 font-mono">
                        {run.run_id}
                      </span>
                    </div>

                    {/* Metrics */}
                    <div className="grid sm:grid-cols-4 gap-2 mt-3">
                      {Object.entries(run.metrics || {}).slice(0, 4).map(([key, values]) => (
                        <div key={key} className="bg-white p-2 rounded text-center">
                          <div className="text-xs text-slate-500 capitalize">{key}</div>
                          <div className="font-mono font-bold text-slate-900">
                            {(values[values.length - 1]?.value || 0).toFixed(3)}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Params */}
                    <div className="flex flex-wrap gap-1 mt-3">
                      {Object.entries(run.params || {}).slice(0, 5).map(([key, value]) => (
                        <span key={key} className="text-xs bg-slate-200 px-2 py-0.5 rounded">
                          {key}: {value}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-slate-500 text-center py-8">
                Select an experiment to view its runs
              </p>
            )}
          </div>
        </div>
      )}

      {/* Models Tab */}
      {selectedTab === 'models' && (
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Models List */}
          <div className="card p-4">
            <h3 className="font-bold text-slate-900 mb-4">Registered Models</h3>
            <div className="space-y-2">
              {(models || []).map(model => (
                <button
                  key={model.name}
                  onClick={() => setSelectedModel(model.name)}
                  className={clsx(
                    'w-full text-left p-3 rounded-lg transition-all',
                    selectedModel === model.name
                      ? 'bg-orange-100 border-2 border-orange-500'
                      : 'bg-slate-50 hover:bg-slate-100 border-2 border-transparent'
                  )}
                >
                  <div className="font-medium text-slate-900">{model.name}</div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                    <Tag className="w-3 h-3" />
                    <span>v{model.latest_version}</span>
                    <span>•</span>
                    <span>{model.total_versions} version(s)</span>
                  </div>
                </button>
              ))}
              {models?.length === 0 && (
                <p className="text-slate-500 text-sm text-center py-4">
                  No models registered
                </p>
              )}
            </div>
          </div>

          {/* Model Details */}
          <div className="card p-4 lg:col-span-2">
            <h3 className="font-bold text-slate-900 mb-4">
              {selectedModel ? `Model: ${selectedModel}` : 'Select a model'}
            </h3>

            {selectedModel && modelDetails ? (
              <div className="space-y-4">
                <p className="text-sm text-slate-600">{modelDetails.description}</p>

                {/* Versions */}
                <div className="space-y-3">
                  <h4 className="font-semibold text-slate-800">Versions</h4>
                  {(modelDetails.versions || []).map(version => (
                    <div key={version.version} className={clsx(
                      'p-4 rounded-lg border-2',
                      STAGE_COLORS[version.stage]
                    )}>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <GitBranch className="w-4 h-4" />
                          <span className="font-bold">Version {version.version}</span>
                          <span className={clsx(
                            'text-xs px-2 py-0.5 rounded-full uppercase font-medium',
                            STAGE_COLORS[version.stage]
                          )}>
                            {version.stage}
                          </span>
                        </div>
                        
                        {/* Stage Transition Buttons */}
                        <div className="flex gap-1">
                          {version.stage !== 'production' && (
                            <button
                              onClick={() => transitionMutation.mutate({
                                name: selectedModel,
                                version: version.version,
                                stage: 'production'
                              })}
                              className="text-xs bg-green-600 text-white px-2 py-1 rounded hover:bg-green-700"
                            >
                              → Production
                            </button>
                          )}
                          {version.stage !== 'archived' && version.stage !== 'production' && (
                            <button
                              onClick={() => transitionMutation.mutate({
                                name: selectedModel,
                                version: version.version,
                                stage: 'archived'
                              })}
                              className="text-xs bg-slate-500 text-white px-2 py-1 rounded hover:bg-slate-600"
                            >
                              Archive
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Metrics */}
                      <div className="grid sm:grid-cols-4 gap-2 mt-3">
                        {Object.entries(version.metrics || {}).map(([key, value]) => (
                          <div key={key} className="bg-white/50 p-2 rounded text-center">
                            <div className="text-xs opacity-70 capitalize">{key}</div>
                            <div className="font-mono font-bold">
                              {typeof value === 'number' ? value.toFixed(3) : value}
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="text-xs opacity-60 mt-2">
                        Registered: {version.registered_at?.slice(0, 10)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-slate-500 text-center py-8">
                Select a model to view its versions
              </p>
            )}
          </div>
        </div>
      )}

      {/* Info */}
      <div className="card p-5 bg-orange-50 border-orange-200">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-orange-800">About MLflow Tracking</h3>
            <p className="text-sm text-orange-700 mt-1">
              MLflow provides experiment tracking and model versioning for ML workflows.
              Track parameters, metrics, and artifacts across training runs. Register models
              and manage their lifecycle through staging → production → archived stages.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
