import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { Activity, TrendingUp, Database, Zap, Loader2 } from 'lucide-react'
import clsx from 'clsx'

const COLORS = ['#3b82f6','#10b981','#f59e0b','#ec4899','#8b5cf6','#ef4444']

function StatCard({ icon: Icon, label, value, sub, color = 'bg-brand-50 text-brand-600' }) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="w-[18px] h-[18px]" />
        </div>
        <span className="text-sm font-medium text-slate-500">{label}</span>
      </div>
      <p className="text-3xl font-bold text-slate-900">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  )
}

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => api.get('/analytics').then(r => r.data),
    refetchInterval: 30000,
    retry: false,
  })

  if (isLoading) return (
    <div className="flex items-center gap-3 py-20 justify-center text-slate-500">
      <Loader2 className="w-5 h-5 animate-spin" /> Loading analytics…
    </div>
  )

  const diseaseData = Object.entries(data?.by_disease ?? {}).map(([k, v]) => ({
    name: k.charAt(0).toUpperCase() + k.slice(1), value: v
  }))
  const modelData = Object.entries(data?.by_model ?? {}).map(([k, v]) => ({
    name: k.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase()).slice(0,12), value: v
  }))
  const dailyData = (data?.daily_counts ?? []).map(d => ({
    date: d.date?.slice(5), count: d.count
  }))

  const cache = data?.cache_stats ?? {}

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Analytics Dashboard</h1>
        <p className="text-slate-500 mt-1">Live prediction statistics and system performance</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Activity}   label="Total Predictions" value={data?.total_predictions ?? 0} color="bg-brand-50 text-brand-600" />
        <StatCard icon={TrendingUp} label="Predictions Today" value={data?.predictions_today ?? 0} color="bg-emerald-50 text-emerald-600" />
        <StatCard icon={Database}   label="Positive Rate"     value={`${((data?.positive_rate ?? 0)*100).toFixed(1)}%`} sub="Across all diseases" color="bg-amber-50 text-amber-600" />
        <StatCard icon={Zap}        label="Avg Confidence"    value={`${((data?.avg_confidence ?? 0)*100).toFixed(1)}%`} sub={`Cache: ${cache.backend ?? '—'}`} color="bg-purple-50 text-purple-600" />
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-3 gap-5">
        {/* Daily trend */}
        <div className="card p-5 lg:col-span-2">
          <h3 className="font-bold text-slate-900 mb-4">Predictions (Last 30 Days)</h3>
          {dailyData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={dailyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ borderRadius: 10, fontSize: 12 }} />
                <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-slate-400 text-sm">
              No prediction history yet — run some predictions first
            </div>
          )}
        </div>

        {/* Disease distribution */}
        <div className="card p-5">
          <h3 className="font-bold text-slate-900 mb-4">By Disease</h3>
          {diseaseData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={diseaseData} cx="50%" cy="50%" outerRadius={70}
                  dataKey="value" label={({name, value}) => `${name}: ${value}`}
                  labelLine={false} fontSize={11}>
                  {diseaseData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 10, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-slate-400 text-sm">No data yet</div>
          )}
        </div>
      </div>

      {/* Model usage + cache */}
      <div className="grid lg:grid-cols-2 gap-5">
        <div className="card p-5">
          <h3 className="font-bold text-slate-900 mb-4">Model Usage</h3>
          {modelData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={modelData} layout="vertical" margin={{ left: 80 }}>
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={80} />
                <Tooltip contentStyle={{ borderRadius: 10, fontSize: 12 }} />
                <Bar dataKey="value" radius={[0,4,4,0]}>
                  {modelData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-40 flex items-center justify-center text-slate-400 text-sm">No data yet</div>
          )}
        </div>

        <div className="card p-5">
          <h3 className="font-bold text-slate-900 mb-4">Cache Performance</h3>
          <div className="space-y-3 mt-2">
            {[
              { label: 'Backend',    value: cache.backend ?? '—' },
              { label: 'Total Keys', value: cache.total_keys ?? 0 },
              { label: 'Cache Hits', value: cache.hits ?? '—' },
              { label: 'Cache Misses', value: cache.misses ?? '—' },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between items-center py-2 border-b border-slate-100 last:border-0">
                <span className="text-sm text-slate-500">{label}</span>
                <span className="text-sm font-semibold text-slate-800 font-mono">{String(value)}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 p-3 rounded-xl bg-slate-50 text-xs text-slate-500">
            Redis provides ~50ms cache hits vs ~300ms fresh inference.
            Falls back to in-process cache if Redis unavailable.
          </div>
        </div>
      </div>
    </div>
  )
}
