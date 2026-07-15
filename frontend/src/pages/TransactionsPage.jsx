import { useState, useEffect, useCallback } from 'react'
import api from '../services/fraud_api'
import RiskScore from '../components/RiskScore'
import TransactionCard from '../components/TransactionCard'
import { format } from 'date-fns'

const STATUS_OPTIONS = ['', 'pending', 'approved', 'declined', 'review', 'fraud']
const PAGE_SIZE = 20

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedTx, setSelectedTx] = useState(null)
  const [filters, setFilters] = useState({
    user_id: '',
    status: '',
    min_amount: '',
    max_amount: '',
    start_date: '',
    end_date: '',
  })

  const fetchTransactions = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const cleanFilters = {}
      Object.entries(filters).forEach(([k, v]) => {
        if (v !== '') cleanFilters[k] = v
      })
      cleanFilters.page = page
      cleanFilters.page_size = PAGE_SIZE
      const data = await api.listTransactions(cleanFilters)
      setTransactions(data.transactions || [])
      setTotal(data.total || 0)
      setTotalPages(data.total_pages || 1)
    } catch (err) {
      setError(err.message)
      setTransactions([])
    } finally {
      setLoading(false)
    }
  }, [filters, page])

  useEffect(() => {
    fetchTransactions()
  }, [fetchTransactions])

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    setPage(1)
  }

  const clearFilters = () => {
    setFilters({
      user_id: '',
      status: '',
      min_amount: '',
      max_amount: '',
      start_date: '',
      end_date: '',
    })
    setPage(1)
  }

  const statusBadge = (status) => {
    const cls = {
      approved: 'badge-green',
      pending: 'badge-yellow',
      declined: 'badge-red',
      review: 'badge-blue',
      fraud: 'badge-red',
    }[status?.toLowerCase()] || 'badge-slate'
    return <span className={`${cls} capitalize`}>{status || '-'}</span>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Transactions</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          {total > 0 ? `${total.toLocaleString()} total transactions` : 'Monitor and review transactions'}
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">User ID</label>
          <input
            type="text"
            className="input-field w-32"
            placeholder="user_123"
            value={filters.user_id}
            onChange={(e) => handleFilterChange('user_id', e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Status</label>
          <select
            className="select-field w-28"
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s || 'All'}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Min Amount</label>
          <input
            type="number"
            className="input-field w-28"
            placeholder="0"
            value={filters.min_amount}
            onChange={(e) => handleFilterChange('min_amount', e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Max Amount</label>
          <input
            type="number"
            className="input-field w-28"
            placeholder="10000"
            value={filters.max_amount}
            onChange={(e) => handleFilterChange('max_amount', e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">From</label>
          <input
            type="date"
            className="input-field w-36"
            value={filters.start_date}
            onChange={(e) => handleFilterChange('start_date', e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">To</label>
          <input
            type="date"
            className="input-field w-36"
            value={filters.end_date}
            onChange={(e) => handleFilterChange('end_date', e.target.value)}
          />
        </div>
        <button onClick={clearFilters} className="btn-secondary text-xs">
          Clear
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 text-left font-medium text-slate-500">ID</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">User</th>
                <th className="px-4 py-3 text-right font-medium text-slate-500">Amount</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Status</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Merchant</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Channel</th>
                <th className="px-4 py-3 text-center font-medium text-slate-500">Risk Score</th>
                <th className="px-4 py-3 text-right font-medium text-slate-500">Time</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-sm text-slate-400">
                    Loading...
                  </td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-sm text-slate-400">
                    No transactions found
                  </td>
                </tr>
              ) : (
                transactions.map((tx) => (
                  <tr
                    key={tx.transaction_id}
                    className="cursor-pointer border-b border-slate-100 transition-colors hover:bg-slate-50"
                    onClick={() => setSelectedTx(tx)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">
                      {(tx.transaction_id || '').slice(0, 12)}...
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-800">{tx.user_id}</td>
                    <td className="px-4 py-3 text-right font-medium text-slate-800">
                      {tx.currency || 'USD'} {tx.amount?.toFixed(2)}
                    </td>
                    <td className="px-4 py-3">{statusBadge(tx.status)}</td>
                    <td className="px-4 py-3 text-slate-600">{tx.merchant_id}</td>
                    <td className="px-4 py-3 capitalize text-slate-600">{tx.channel || '-'}</td>
                    <td className="px-4 py-3 text-center">
                      {tx.fraud_score !== undefined ? (
                        <RiskScore score={tx.fraud_score} size="sm" showLabel={false} />
                      ) : (
                        <span className="text-xs text-slate-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-slate-400">
                      {tx.created_at && format(new Date(tx.created_at), 'HH:mm:ss')}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3">
          <p className="text-xs text-slate-500">
            Showing {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, total)} of {total}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              className="btn-secondary px-3 py-1.5 text-xs"
            >
              Previous
            </button>
            <span className="text-xs text-slate-500">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className="btn-secondary px-3 py-1.5 text-xs"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Detail Modal */}
      {selectedTx && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setSelectedTx(null)}>
          <div className="fixed inset-0 bg-black/30" />
          <div
            className="relative z-10 w-full max-w-2xl overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between rounded-t-xl border-b border-slate-200 bg-white px-5 py-4">
              <h2 className="text-base font-semibold text-slate-900">Transaction Details</h2>
              <button
                onClick={() => setSelectedTx(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <TransactionCard transaction={selectedTx} detailed />
          </div>
        </div>
      )}
    </div>
  )
}
