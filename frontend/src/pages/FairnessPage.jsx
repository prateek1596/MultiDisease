import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import toast from 'react-hot-toast'
import {
  Scale, Play, Loader2, CheckCircle, XCircle,
  AlertTriangle, Info, Plus, Trash2, RefreshCw
} from 'lucide-react'
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, Cell
} from 'recharts'
import clsx from 'clsx'
import { getApiErrorMessage } from '../utils/apiError'

// ── Constants ─────────────────────────────────────────────────────────────────
const DISEASES      = ['heart', 'diabetes', 'kidney']
const DISEASE_EMOJI = { heart: '🫀', diabetes: '🩸', kidney: '🫘' }
const GROUP_COLORS  = ['#3b82f6', '#ec4899', '#f59e0b', '#10b981', '#8b5cf6']

const METRIC_META = {
  demographic_parity: { label: 'Demographic Parity',  desc: '|P(Ŷ=1|A=0) − P(Ŷ=1|A=1)|  < 0.10' },
  equal_opportunity:  { label: 'Equal Opportunity',   desc: '|TPR_A − TPR_B|  < 0.10' },
  disparate_impact:   { label: 'Disparate Impact',    desc: 'min/max pos-rate ratio  0.80–1.25' },
  predictive_parity:  { label: 'Predictive Parity',  desc: '|PPV_A − PPV_B|  < 0.10' },
}

// ── Sub-components ────────────────────────────────────────────────────────────

function MetricCard({ name, data }) {
  const meta = METRIC_META[name] ?? { label: name, desc: '' }
  const fair = data?.is_fair ?? false
  const val  = typeof data?.value === 'number' ? data.value.toFixed(4) : '—'

  return (
    <div className={clsx(
      'rounded-2xl border-2 p-4 transition-all',
      fair
        ? 'border-emerald-300 bg-emerald-50'
        : 'border-red-300 bg-red-50'
    )}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-xs font-bold text-slate-600 uppercase tracking-wide leading-tight">
          {meta.label}
        </p>
        {fair
          ? <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
          : <XCircle     className="w-4 h-4 text-red-500    flex-shrink-0 mt-0.5" />
        }
      </div>
      <p className="text-3xl font-bold font-mono text-slate-900">{val}</p>
      <p className="text-[11px] text-slate-400 mt-1">{meta.desc}</p>
      <span className={clsx(
        'inline-block mt-2 px-2 py-0.5 rounded-full text-[11px] font-bold',
        fair ? 'bg-emerald-200 text-emerald-800' : 'bg-red-200 text-red-800'
      )}>
        {fair ? '✓ FAIR' : '⚠ NEEDS ATTENTION'}
      </span>
    </div>
  )
}

function GroupRow({ group, index, onChange, onRemove, canRemove }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="w-3 h-3 rounded-full flex-shrink-0"
        style={{ background: GROUP_COLORS[index % GROUP_COLORS.length] }}
      />
      <input
        value={group.label}
        onChange={e => onChange(index, 'label', e.target.value)}
        placeholder={`Group ${index + 1} name`}
        className="input-field flex-1"
      />
      <div className="flex items-center gap-2 w-36">
        <input
          type="number" min={1} max={99} value={group.pct}
          onChange={e => onChange(index, 'pct', Number(e.target.value))}
          className="input-field w-20 text-center"
        />
        <span className="text-sm text-slate-500 font-medium">%</span>
      </div>
      {canRemove && (
        <button onClick={() => onRemove(index)}
          className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors">
          <Trash2 className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function FairnessPage() {
  const [disease,   setDisease]   = useState('heart')
  const [attrName,  setAttrName]  = useState('Gender')
  const [groups,    setGroups]    = useState([
    { label: 'Male',   pct: 60 },
    { label: 'Female', pct: 40 },
  ])
  const [result, setResult] = useState(null)

  // Fetch actual test-set size whenever disease changes
  const { data: infoData, isLoading: infoLoading } = useQuery({
    queryKey: ['fairness-info', disease],
    queryFn: () => api.get(`/fairness/${disease}/info`).then(r => r.data),
    retry: false,
  })
  const testSize = infoData?.test_size ?? null

  // Computed pct total
  const pctTotal = groups.reduce((s, g) => s + g.pct, 0)
  const pctOk    = Math.abs(pctTotal - 100) < 1

  // Group helpers
  const updateGroup = (idx, field, val) => {
    setGroups(prev => prev.map((g, i) => i === idx ? { ...g, [field]: val } : g))
  }
  const addGroup = () => {
    if (groups.length >= 5) return
    const remaining = Math.max(1, 100 - pctTotal)
    setGroups(prev => [...prev, { label: `Group ${prev.length + 1}`, pct: remaining }])
  }
  const removeGroup = idx => {
    if (groups.length <= 2) return
    setGroups(prev => prev.filter((_, i) => i !== idx))
  }

  // Mutation
  const mutation = useMutation({
    mutationFn: () =>
      api.post(`/fairness/${disease}`, {
        groups:     groups.map(g => ({ label: g.label, pct: g.pct })),
        attr_name:  attrName,
        model_name: 'best',
      }).then(r => r.data),
    onSuccess: data => {
      setResult(data)
      toast.success('Fairness analysis complete!')
    },
    onError: err => {
      const msg = getApiErrorMessage(err, 'Analysis failed')
      toast.error(msg)
    },
  })

  // Radar chart data
  const buildRadarData = () => {
    if (!result?.metrics) return []
    const m      = result.metrics
    const grps   = result.groups ?? []
    const rows   = [
      { metric: 'Pos. Rate',  key: 'group_rates',  src: m.demographic_parity },
      { metric: 'TPR',        key: 'TPR_by_group',  src: m.equal_opportunity  },
      { metric: 'PPV',        key: 'PPV_by_group',  src: m.predictive_parity  },
    ]
    return rows.map(({ metric, key, src }) => {
      const row = { metric }
      grps.forEach(g => { row[g] = src?.[key]?.[g] ?? 0 })
      return row
    })
  }

  // Bar chart data — group positive rates
  const buildBarData = () => {
    if (!result?.metrics?.demographic_parity?.group_rates) return []
    return Object.entries(result.metrics.demographic_parity.group_rates).map(([g, v]) => ({
      group: g, rate: parseFloat((v * 100).toFixed(2))
    }))
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <Scale className="w-8 h-8 text-brand-600" />
          Fairness Analysis
        </h1>
        <p className="text-slate-500 mt-1">
          Evaluate model equity across demographic groups — Demographic Parity, Equal Opportunity, Disparate Impact
        </p>
      </div>

      {/* Info box */}
      <div className="rounded-xl bg-blue-50 border border-blue-200 p-4 flex gap-3 text-sm text-blue-800">
        <Info className="w-5 h-5 flex-shrink-0 mt-0.5 text-blue-500" />
        <p>
          Define demographic groups and their proportions. The system automatically
          generates a representative attribute array matching the test-set size
          ({testSize ? <strong>{testSize} samples</strong> : 'loading…'}) and runs all fairness metrics.
        </p>
      </div>

      {/* Config card */}
      <div className="card p-6 space-y-5">
        <h2 className="font-bold text-slate-900 text-lg">Configuration</h2>

        {/* Disease selector */}
        <div>
          <label className="block text-sm font-semibold text-slate-600 mb-2">Disease Dataset</label>
          <div className="flex gap-3 flex-wrap">
            {DISEASES.map(d => (
              <button key={d}
                onClick={() => { setDisease(d); setResult(null) }}
                className={clsx(
                  'px-4 py-2.5 rounded-xl border-2 text-sm font-semibold transition-all',
                  disease === d
                    ? 'border-brand-500 bg-brand-50 text-brand-700 shadow-sm'
                    : 'border-slate-200 text-slate-500 hover:border-slate-300 bg-white'
                )}>
                {DISEASE_EMOJI[d]} {d.charAt(0).toUpperCase() + d.slice(1)}
                {disease === d && testSize && (
                  <span className="ml-2 text-xs font-normal text-brand-400">
                    ({testSize} test samples)
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Attribute name */}
        <div className="max-w-xs">
          <label className="block text-xs font-semibold text-slate-600 mb-1.5">
            Sensitive Attribute Name
          </label>
          <input
            value={attrName}
            onChange={e => setAttrName(e.target.value)}
            placeholder="e.g. Gender, Age Group, Race"
            className="input-field"
          />
        </div>

        {/* Groups */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <label className="text-xs font-semibold text-slate-600">
              Group Splits
              <span className={clsx(
                'ml-2 font-bold',
                pctOk ? 'text-emerald-600' : 'text-red-500'
              )}>
                (total: {pctTotal}% {pctOk ? '✓' : '— must equal 100%'})
              </span>
            </label>
            {groups.length < 5 && (
              <button onClick={addGroup}
                className="flex items-center gap-1.5 text-xs font-semibold text-brand-600 hover:text-brand-700">
                <Plus className="w-3.5 h-3.5" /> Add Group
              </button>
            )}
          </div>
          <div className="space-y-2.5">
            {groups.map((g, i) => (
              <GroupRow
                key={i} group={g} index={i}
                onChange={updateGroup}
                onRemove={removeGroup}
                canRemove={groups.length > 2}
              />
            ))}
          </div>
        </div>

        {/* Run button */}
        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !pctOk || infoLoading}
            className="btn-primary flex items-center gap-2"
          >
            {mutation.isPending
              ? <><Loader2 className="w-4 h-4 animate-spin" />Analysing…</>
              : <><Play className="w-4 h-4" />Run Fairness Analysis</>
            }
          </button>
          {result && (
            <button onClick={() => setResult(null)}
              className="btn-secondary flex items-center gap-2 text-sm">
              <RefreshCw className="w-3.5 h-3.5" /> Reset
            </button>
          )}
        </div>
      </div>

      {/* ── Results ─────────────────────────────────────────────────────────── */}
      {result && (
        <div className="space-y-5 animate-in">

          {/* Overall verdict */}
          <div className={clsx(
            'card border-2 p-5 flex items-start gap-4',
            result.is_fair_overall
              ? 'border-emerald-400 bg-emerald-50'
              : 'border-amber-400 bg-amber-50'
          )}>
            {result.is_fair_overall
              ? <CheckCircle  className="w-10 h-10 text-emerald-500 flex-shrink-0 mt-0.5" />
              : <AlertTriangle className="w-10 h-10 text-amber-500 flex-shrink-0 mt-0.5" />
            }
            <div className="flex-1">
              <h3 className={clsx('text-xl font-bold',
                result.is_fair_overall ? 'text-emerald-800' : 'text-amber-800')}>
                {result.is_fair_overall
                  ? '✅ No Major Fairness Issues Detected'
                  : `⚠️ ${result.fairness_issues?.length} Fairness Issue(s) Found`}
              </h3>
              <div className="flex flex-wrap gap-4 mt-2 text-sm text-slate-600">
                <span>Overall accuracy: <strong>{(result.overall_accuracy * 100).toFixed(2)}%</strong></span>
                <span>Test samples: <strong>{result.test_size ?? result.sample_size}</strong></span>
                <span>Model: <strong className="capitalize">{result.model_used?.replace(/_/g,' ')}</strong></span>
              </div>
              {result.fairness_issues?.length > 0 && (
                <p className="text-sm text-amber-700 mt-2 font-medium">
                  Issues: {result.fairness_issues.join(' · ')}
                </p>
              )}
            </div>
          </div>

          {/* Metric cards */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(result.metrics ?? {}).map(([key, data]) => (
              <MetricCard key={key} name={key} data={data} />
            ))}
          </div>

          {/* Charts row */}
          <div className="grid lg:grid-cols-2 gap-5">
            {/* Positive prediction rate bar chart */}
            <div className="card p-5">
              <h3 className="font-bold text-slate-900 mb-4 text-sm">
                Positive Prediction Rate by Group
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={buildBarData()} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="group" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 11 }} unit="%" domain={[0, 100]} />
                  <Tooltip formatter={v => `${v}%`} contentStyle={{ borderRadius: 10, fontSize: 12 }} />
                  <Bar dataKey="rate" radius={[6, 6, 0, 0]}>
                    {buildBarData().map((_, i) => (
                      <Cell key={i} fill={GROUP_COLORS[i % GROUP_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Radar chart */}
            <div className="card p-5">
              <h3 className="font-bold text-slate-900 mb-4 text-sm">
                Multi-Metric Fairness Radar
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <RadarChart data={buildRadarData()}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
                  {result.groups?.map((g, i) => (
                    <Radar key={g} name={g} dataKey={g}
                      stroke={GROUP_COLORS[i % GROUP_COLORS.length]}
                      fill={GROUP_COLORS[i % GROUP_COLORS.length]}
                      fillOpacity={0.12}
                    />
                  ))}
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={v => typeof v === 'number' ? v.toFixed(4) : v}
                    contentStyle={{ borderRadius: 10, fontSize: 12 }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Group sizes + detailed metric values */}
          <div className="card p-5">
            <h3 className="font-bold text-slate-900 mb-4 text-sm">
              Detailed Metrics by Group
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase">
                  <tr>
                    <th className="px-4 py-2.5 text-left">Group</th>
                    <th className="px-4 py-2.5 text-left">Size</th>
                    <th className="px-4 py-2.5 text-left">Pos. Rate</th>
                    <th className="px-4 py-2.5 text-left">TPR</th>
                    <th className="px-4 py-2.5 text-left">PPV</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {result.groups?.map((g, i) => {
                    const posRate = result.metrics?.demographic_parity?.group_rates?.[g] ?? null
                    const tpr     = result.metrics?.equal_opportunity?.TPR_by_group?.[g]  ?? null
                    const ppv     = result.metrics?.predictive_parity?.PPV_by_group?.[g]  ?? null
                    const size    = result.group_sizes?.[g] ?? '—'
                    const fmt     = v => v !== null ? (v * 100).toFixed(2) + '%' : '—'
                    return (
                      <tr key={g} className="hover:bg-slate-50">
                        <td className="px-4 py-2.5 font-semibold text-slate-800 flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full inline-block"
                            style={{ background: GROUP_COLORS[i % GROUP_COLORS.length] }} />
                          {g}
                        </td>
                        <td className="px-4 py-2.5 text-slate-600">{size}</td>
                        <td className="px-4 py-2.5 font-mono text-slate-700">{fmt(posRate)}</td>
                        <td className="px-4 py-2.5 font-mono text-slate-700">{fmt(tpr)}</td>
                        <td className="px-4 py-2.5 font-mono text-slate-700">{fmt(ppv)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}
    </div>
  )
}
