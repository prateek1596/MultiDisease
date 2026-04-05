import { useState } from 'react'
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import clsx from 'clsx'

export default function LimeExplanation({ explanation, className }) {
  const [expanded, setExpanded] = useState(false)
  
  if (!explanation || !explanation.available) {
    if (explanation?.error) {
      return (
        <div className={clsx('text-sm text-slate-500 italic', className)}>
          LIME explanation unavailable: {explanation.error}
        </div>
      )
    }
    return null
  }
  
  const { contributions = [] } = explanation
  const visibleContributions = expanded ? contributions : contributions.slice(0, 5)
  
  // Find max absolute contribution for scaling bars
  const maxContrib = Math.max(...contributions.map(c => Math.abs(c.contribution)), 0.001)
  
  return (
    <div className={clsx('space-y-3', className)}>
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
          🔍 LIME Explanation
          <span className="text-xs font-normal text-slate-500">
            (Local Interpretable Model-agnostic Explanations)
          </span>
        </h4>
      </div>
      
      <div className="space-y-2">
        {visibleContributions.map((contrib, idx) => (
          <ContributionBar
            key={idx}
            feature={contrib.feature}
            contribution={contrib.contribution}
            direction={contrib.direction}
            maxContrib={maxContrib}
          />
        ))}
      </div>
      
      {contributions.length > 5 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-medium"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-3 h-3" />
              Show less
            </>
          ) : (
            <>
              <ChevronDown className="w-3 h-3" />
              Show all {contributions.length} features
            </>
          )}
        </button>
      )}
      
      <p className="text-xs text-slate-500">
        Green bars indicate features that increase risk, red bars decrease risk.
        Bar length shows relative importance.
      </p>
    </div>
  )
}

function ContributionBar({ feature, contribution, direction, maxContrib }) {
  const isPositive = contribution > 0
  const percentage = Math.min(Math.abs(contribution) / maxContrib * 100, 100)
  
  const Icon = isPositive ? TrendingUp : contribution < 0 ? TrendingDown : Minus
  
  return (
    <div className="flex items-center gap-3">
      <div className="w-40 flex-shrink-0">
        <span className="text-xs text-slate-600 truncate block" title={feature}>
          {formatFeatureRule(feature)}
        </span>
      </div>
      
      <div className="flex-1 flex items-center gap-2">
        {/* Negative side */}
        <div className="w-1/2 flex justify-end">
          {!isPositive && (
            <div
              className="h-4 bg-emerald-400 rounded-l transition-all duration-300"
              style={{ width: `${percentage}%` }}
            />
          )}
        </div>
        
        {/* Center line */}
        <div className="w-px h-6 bg-slate-300" />
        
        {/* Positive side */}
        <div className="w-1/2">
          {isPositive && (
            <div
              className="h-4 bg-red-400 rounded-r transition-all duration-300"
              style={{ width: `${percentage}%` }}
            />
          )}
        </div>
      </div>
      
      <div className="w-16 flex-shrink-0 text-right">
        <span className={clsx(
          'text-xs font-medium',
          isPositive ? 'text-red-600' : 'text-emerald-600'
        )}>
          {contribution > 0 ? '+' : ''}{contribution.toFixed(3)}
        </span>
      </div>
      
      <Icon className={clsx(
        'w-4 h-4 flex-shrink-0',
        isPositive ? 'text-red-500' : 'text-emerald-500'
      )} />
    </div>
  )
}

function formatFeatureRule(rule) {
  // LIME returns rules like "glucose > 150" or "age <= 45"
  // Make them more readable
  return rule
    .replace(/_/g, ' ')
    .replace(/\b(\w)/g, c => c.toUpperCase())
}
