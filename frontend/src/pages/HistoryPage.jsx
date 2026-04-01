import { useQuery } from '@tanstack/react-query'
import { predictAPI } from '../api/client'
import { History, CheckCircle, XCircle, Loader2, ClipboardList } from 'lucide-react'
import clsx from 'clsx'

const DISEASE_EMOJI = { heart: '🫀', diabetes: '🩸', kidney: '🫘' }

export default function HistoryPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['history'],
    queryFn: () => predictAPI.history().then((r) => r.data),
    retry: false,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Prediction History</h1>
        <p className="text-slate-500 mt-1">All predictions made with your account</p>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-3 text-slate-500 py-10 justify-center">
          <Loader2 className="w-5 h-5 animate-spin" />Loading history…
        </div>
      ) : !data?.length ? (
        <div className="card p-12 text-center">
          <ClipboardList className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="font-bold text-slate-700 text-lg">No Predictions Yet</h3>
          <p className="text-slate-500 text-sm mt-1">Run your first prediction from the Predict page</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
            <History className="w-4 h-4 text-slate-500" />
            <h2 className="font-bold text-slate-900">Recent Predictions ({data.length})</h2>
          </div>
          <div className="divide-y divide-slate-100">
            {data.map((record) => (
              <div key={record.id} className="px-5 py-4 flex items-center gap-4 hover:bg-slate-50 transition-colors">
                <div className="text-2xl">{DISEASE_EMOJI[record.disease_type] ?? '🏥'}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-slate-800 capitalize">{record.disease_type}</span>
                    <span className={clsx(
                      'badge text-[11px]',
                      record.prediction_result === 1 ? 'badge-red' : 'badge-green'
                    )}>
                      {record.prediction_result === 1
                        ? <><XCircle className="w-3 h-3" /> Positive</>
                        : <><CheckCircle className="w-3 h-3" /> Negative</>
                      }
                    </span>
                    <span className="badge badge-blue text-[11px]">{record.model_used.replace(/_/g,' ')}</span>
                  </div>
                  <p className="text-sm text-slate-500 mt-0.5 truncate">{record.prediction_label}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-slate-800">
                    {(record.confidence * 100).toFixed(1)}%
                  </p>
                  <p className="text-xs text-slate-400">
                    {record.created_at
                      ? new Date(record.created_at).toLocaleDateString('en-US', {
                          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                        })
                      : '—'
                    }
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
