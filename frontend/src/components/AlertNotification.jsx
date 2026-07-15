import { format } from 'date-fns'

const SEVERITY_STYLES = {
  critical: { dot: 'bg-red-500', bg: 'bg-red-50 border-red-200', label: 'text-red-800' },
  high: { dot: 'bg-orange-500', bg: 'bg-orange-50 border-orange-200', label: 'text-orange-800' },
  medium: { dot: 'bg-amber-500', bg: 'bg-amber-50 border-amber-200', label: 'text-amber-800' },
  low: { dot: 'bg-blue-500', bg: 'bg-blue-50 border-blue-200', label: 'text-blue-800' },
}

const STATUS_BADGES = {
  open: 'badge-red',
  acknowledged: 'badge-yellow',
  investigating: 'badge-blue',
  resolved: 'badge-green',
  false_positive: 'badge-slate',
}

export default function AlertNotification({ alert, onAcknowledge }) {
  const severity = (alert.severity || 'low').toLowerCase()
  const status = (alert.status || 'open').toLowerCase()
  const styles = SEVERITY_STYLES[severity] || SEVERITY_STYLES.low
  const badgeClass = STATUS_BADGES[status] || 'badge-slate'

  return (
    <div className={`rounded-lg border p-4 ${styles.bg}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <span className={`mt-1 inline-block h-2.5 w-2.5 shrink-0 rounded-full ${styles.dot}`} />
          <div>
            <div className="flex items-center gap-2">
              <span className={`text-xs font-semibold uppercase ${styles.label}`}>{severity}</span>
              <span className={`${badgeClass} capitalize`}>{status}</span>
              <span className="text-xs text-slate-400">
                {alert.created_at && format(new Date(alert.created_at), 'MMM d, HH:mm')}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-800">{alert.description}</p>
            {alert.triggered_rules && alert.triggered_rules.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {alert.triggered_rules.map((rule, i) => (
                  <span key={i} className="rounded bg-white/60 px-2 py-0.5 text-xs text-slate-600">
                    {rule}
                  </span>
                ))}
              </div>
            )}
            <div className="mt-2 flex items-center gap-4 text-xs text-slate-500">
              <span>Transaction: {alert.transaction_id}</span>
              <span>User: {alert.user_id}</span>
              {alert.fraud_score !== undefined && (
                <span>Score: {(alert.fraud_score * 100).toFixed(0)}%</span>
              )}
            </div>
          </div>
        </div>

        {onAcknowledge && status === 'open' && (
          <button
            onClick={() => onAcknowledge(alert.alert_id)}
            className="btn-secondary shrink-0 text-xs"
          >
            Acknowledge
          </button>
        )}
      </div>
    </div>
  )
}
