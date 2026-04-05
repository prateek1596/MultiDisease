import { AlertTriangle, AlertCircle, Info } from 'lucide-react'
import clsx from 'clsx'

const severityConfig = {
  high: {
    icon: AlertTriangle,
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    textColor: 'text-red-800',
    iconColor: 'text-red-500',
  },
  medium: {
    icon: AlertCircle,
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    textColor: 'text-yellow-800',
    iconColor: 'text-yellow-500',
  },
  low: {
    icon: Info,
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-800',
    iconColor: 'text-blue-500',
  },
}

export default function OutlierAlerts({ alerts, className }) {
  if (!alerts || alerts.length === 0) return null

  return (
    <div className={clsx('space-y-2', className)}>
      <div className="flex items-center gap-2 text-sm font-semibold text-amber-700">
        <AlertTriangle className="w-4 h-4" />
        <span>Input Alerts ({alerts.length})</span>
      </div>
      
      <div className="space-y-2">
        {alerts.map((alert, idx) => {
          const config = severityConfig[alert.severity] || severityConfig.medium
          const Icon = config.icon
          
          return (
            <div
              key={idx}
              className={clsx(
                'flex items-start gap-3 p-3 rounded-lg border',
                config.bgColor,
                config.borderColor
              )}
            >
              <Icon className={clsx('w-5 h-5 flex-shrink-0 mt-0.5', config.iconColor)} />
              <div className="flex-1 min-w-0">
                <div className={clsx('font-medium text-sm', config.textColor)}>
                  {formatFeatureName(alert.feature)}: {alert.value}
                </div>
                <div className={clsx('text-xs mt-0.5', config.textColor, 'opacity-80')}>
                  {alert.reason}
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  Expected range: {alert.expected_range}
                </div>
              </div>
            </div>
          )
        })}
      </div>
      
      <p className="text-xs text-slate-500 mt-2">
        ⚠️ Values outside the training data distribution may affect prediction accuracy.
      </p>
    </div>
  )
}

function formatFeatureName(name) {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

export function OutlierBadge({ count }) {
  if (!count || count === 0) return null
  
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
      <AlertTriangle className="w-3 h-3" />
      {count} alert{count > 1 ? 's' : ''}
    </span>
  )
}
