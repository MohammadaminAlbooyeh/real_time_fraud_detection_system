const RISK_COLORS = {
  low: { bg: 'bg-emerald-100', text: 'text-emerald-800', ring: 'stroke-emerald-500' },
  medium: { bg: 'bg-amber-100', text: 'text-amber-800', ring: 'stroke-amber-500' },
  high: { bg: 'bg-orange-100', text: 'text-orange-800', ring: 'stroke-orange-500' },
  critical: { bg: 'bg-red-100', text: 'text-red-800', ring: 'stroke-red-500' },
}

function getRiskLevel(score) {
  if (score >= 0.8) return 'critical'
  if (score >= 0.6) return 'high'
  if (score >= 0.3) return 'medium'
  return 'low'
}

export default function RiskScore({ score, size = 'md', showLabel = true }) {
  const level = getRiskLevel(score)
  const colors = RISK_COLORS[level]
  const dimension = size === 'sm' ? 36 : size === 'lg' ? 64 : 48
  const strokeWidth = size === 'sm' ? 3 : size === 'lg' ? 5 : 4
  const radius = (dimension - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - score)

  return (
    <div className="inline-flex items-center gap-2">
      <svg width={dimension} height={dimension} className="-rotate-90">
        <circle
          cx={dimension / 2}
          cy={dimension / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-slate-200"
        />
        <circle
          cx={dimension / 2}
          cy={dimension / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={colors.ring}
        />
      </svg>
      <div>
        <span className={`text-sm font-semibold ${colors.text}`}>
          {(score * 100).toFixed(0)}%
        </span>
        {showLabel && (
          <span className={`ml-1.5 text-xs font-medium capitalize ${colors.text}`}>
            {level}
          </span>
        )}
      </div>
    </div>
  )
}
