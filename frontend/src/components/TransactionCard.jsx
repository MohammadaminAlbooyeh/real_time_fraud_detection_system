import RiskScore from './RiskScore'
import { format } from 'date-fns'

const STATUS_BADGES = {
  approved: 'badge-green',
  pending: 'badge-yellow',
  declined: 'badge-red',
  review: 'badge-blue',
  fraud: 'badge-red',
}

export default function TransactionCard({ transaction, detailed = false }) {
  const status = (transaction.status || 'pending').toLowerCase()
  const badgeClass = STATUS_BADGES[status] || 'badge-slate'

  if (detailed) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-slate-900">Transaction</p>
              <span className={`${badgeClass} capitalize`}>{status}</span>
            </div>
            <p className="mt-0.5 text-xs text-slate-400 font-mono">{transaction.transaction_id}</p>
          </div>
          {transaction.fraud_score !== undefined && (
            <RiskScore score={transaction.fraud_score} />
          )}
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-slate-500">Amount</span>
            <p className="font-medium text-slate-900">
              {transaction.currency || 'USD'} {transaction.amount?.toFixed(2)}
            </p>
          </div>
          <div>
            <span className="text-slate-500">User ID</span>
            <p className="font-medium text-slate-900">{transaction.user_id}</p>
          </div>
          <div>
            <span className="text-slate-500">Merchant</span>
            <p className="font-medium text-slate-900">{transaction.merchant_id}</p>
          </div>
          <div>
            <span className="text-slate-500">Category</span>
            <p className="font-medium text-slate-900">{transaction.merchant_category || '-'}</p>
          </div>
          <div>
            <span className="text-slate-500">Channel</span>
            <p className="font-medium capitalize text-slate-900">{transaction.channel || '-'}</p>
          </div>
          <div>
            <span className="text-slate-500">Country</span>
            <p className="font-medium text-slate-900">{transaction.merchant_country || '-'}</p>
          </div>
          <div>
            <span className="text-slate-500">Device</span>
            <p className="font-medium text-slate-900">{transaction.device_id || '-'}</p>
          </div>
          <div>
            <span className="text-slate-500">Processed</span>
            <p className="font-medium text-slate-900">
              {transaction.processed_at
                ? format(new Date(transaction.processed_at), 'HH:mm:ss')
                : '-'}
            </p>
          </div>
        </div>

        <div className="mt-4 border-t border-slate-100 pt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">Rule Scores</p>
          <div className="flex flex-wrap gap-2">
            {transaction.rule_scores && Object.entries(transaction.rule_scores).map(([rule, score]) => (
              <span key={rule} className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600">
                {rule}: {typeof score === 'number' ? score.toFixed(3) : score}
              </span>
            ))}
            {(!transaction.rule_scores || Object.keys(transaction.rule_scores).length === 0) && (
              <span className="text-xs text-slate-400">No rule data</span>
            )}
          </div>
        </div>

        {transaction.ml_score !== undefined && transaction.ml_score !== null && (
          <div className="mt-3 flex items-center gap-2">
            <span className="text-xs text-slate-500">ML Score:</span>
            <span className="text-xs font-medium text-slate-800">
              {(transaction.ml_score * 100).toFixed(1)}%
            </span>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-100 bg-white px-4 py-3 transition-colors hover:border-slate-200">
      <div className="flex min-w-0 items-center gap-4">
        <span className={`${badgeClass} capitalize shrink-0`}>{status}</span>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-slate-900">
            {transaction.currency || 'USD'} {transaction.amount?.toFixed(2)}
          </p>
          <p className="truncate text-xs text-slate-500 font-mono">
            {transaction.transaction_id}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-4 shrink-0">
        <span className="hidden text-xs text-slate-500 sm:block">{transaction.user_id}</span>
        {transaction.fraud_score !== undefined && (
          <RiskScore score={transaction.fraud_score} size="sm" showLabel={false} />
        )}
      </div>
    </div>
  )
}
