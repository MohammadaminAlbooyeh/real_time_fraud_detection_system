import { useState, useEffect, useCallback } from 'react'
import api from '../services/fraud_api'
import useWebSocket from '../hooks/useWebSocket'
import AlertNotification from '../components/AlertNotification'
import RiskScore from '../components/RiskScore'
import { format } from 'date-fns'

const SEVERITY_OPTIONS = ['', 'low', 'medium', 'high', 'critical']
const STATUS_OPTIONS = ['', 'open', 'acknowledged', 'investigating', 'resolved', 'false_positive']
const PAGE_SIZE = 20

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedAlert, setSelectedAlert] = useState(null)
  const [filters, setFilters] = useState({
    severity: '',
    status: '',
    user_id: '',
    min_fraud_score: '',
  })
  const [liveAlerts, setLiveAlerts] = useState([])

  const fetchAlerts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const cleanFilters = {}
      Object.entries(filters).forEach(([k, v]) => {
        if (v !== '') cleanFilters[k] = v
      })
      cleanFilters.page = page
      cleanFilters.page_size = PAGE_SIZE
      const data = await api.listAlerts(cleanFilters)
      setAlerts(data.alerts || [])
      setTotal(data.total || 0)
      setTotalPages(data.total_pages || 1)
    } catch (err) {
      setError(err.message)
      setAlerts([])
    } finally {
      setLoading(false)
    }
  }, [filters, page])

  useEffect(() => {
    fetchAlerts()
  }, [fetchAlerts])

  useWebSocket('alerts', (msg) => {
    if (msg.type === 'alert' && msg.data) {
      setLiveAlerts((prev) => [msg.data, ...prev].slice(0, 10))
    }
  })

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    setPage(1)
  }

  const clearFilters = () => {
    setFilters({ severity: '', status: '', user_id: '', min_fraud_score: '' })
    setPage(1)
  }

  const handleAcknowledge = async (alertId) => {
    try {
      await api.acknowledgeAlert(alertId, { acknowledged_by: 'dashboard_user' })
      fetchAlerts()
    } catch (err) {
      console.error('Failed to acknowledge:', err)
    }
  }

  const handleResolve = async (alertId) => {
    try {
      await api.updateAlert(alertId, { status: 'resolved', resolution_notes: 'Reviewed via dashboard' })
      fetchAlerts()
    } catch (err) {
      console.error('Failed to resolve:', err)
    }
  }

  const severityDot = (severity) => {
    const colors = {
      critical: 'bg-red-500',
      high: 'bg-orange-500',
      medium: 'bg-amber-500',
      low: 'bg-blue-500',
    }
    return <span className={`inline-block h-2 w-2 rounded-full ${colors[severity] || 'bg-slate-400'}`} />
  }

  const statusBadge = (status) => {
    const cls = {
      open: 'badge-red',
      acknowledged: 'badge-yellow',
      investigating: 'badge-blue',
      resolved: 'badge-green',
      false_positive: 'badge-slate',
    }[status?.toLowerCase()] || 'badge-slate'
    return <span className={`${cls} capitalize`}>{status || '-'}</span>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Alerts</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          {total > 0 ? `${total.toLocaleString()} total alerts` : 'Investigate and manage fraud alerts'}
        </p>
      </div>

      {/* Live Alerts Bar */}
      {liveAlerts.length > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <div className="mb-2 flex items-center gap-2">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-red-500" />
            <span className="text-sm font-semibold text-red-800">New Alerts ({liveAlerts.length})</span>
          </div>
          <div className="space-y-2">
            {liveAlerts.map((alert) => (
              <AlertNotification key={alert.alert_id} alert={alert} onAcknowledge={handleAcknowledge} />
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Severity</label>
          <select
            className="select-field w-28"
            value={filters.severity}
            onChange={(e) => handleFilterChange('severity', e.target.value)}
          >
            {SEVERITY_OPTIONS.map((s) => (
              <option key={s} value={s}>{s || 'All'}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Status</label>
          <select
            className="select-field w-32"
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s || 'All'}</option>
            ))}
          </select>
        </div>
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
          <label className="mb-1 block text-xs font-medium text-slate-500">Min Score</label>
          <input
            type="number"
            className="input-field w-24"
            placeholder="0.5"
            min="0"
            max="1"
            step="0.1"
            value={filters.min_fraud_score}
            onChange={(e) => handleFilterChange('min_fraud_score', e.target.value)}
          />
        </div>
        <button onClick={clearFilters} className="btn-secondary text-xs">Clear</button>
        <button onClick={fetchAlerts} className="btn-primary text-xs" disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
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
                <th className="px-4 py-3 text-left font-medium text-slate-500">Severity</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Status</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Description</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">User</th>
                <th className="px-4 py-3 text-center font-medium text-slate-500">Score</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500">Rules</th>
                <th className="px-4 py-3 text-right font-medium text-slate-500">Time</th>
                <th className="px-4 py-3 text-center font-medium text-slate-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-sm text-slate-400">Loading...</td>
                </tr>
              ) : alerts.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-sm text-slate-400">No alerts found</td>
                </tr>
              ) : (
                alerts.map((alert) => (
                  <tr
                    key={alert.alert_id}
                    className="cursor-pointer border-b border-slate-100 transition-colors hover:bg-slate-50"
                    onClick={() => setSelectedAlert(alert)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {severityDot(alert.severity)}
                        <span className="font-medium capitalize text-slate-800">{alert.severity}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">{statusBadge(alert.status)}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-slate-600">
                      {alert.description}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{alert.user_id}</td>
                    <td className="px-4 py-3 text-center">
                      {alert.fraud_score !== undefined ? (
                        <RiskScore score={alert.fraud_score} size="sm" showLabel={false} />
                      ) : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {(alert.triggered_rules || []).slice(0, 2).map((r, i) => (
                          <span key={i} className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
                            {r}
                          </span>
                        ))}
                        {(alert.triggered_rules || []).length > 2 && (
                          <span className="text-xs text-slate-400">+{alert.triggered_rules.length - 2}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-slate-400">
                      {alert.created_at && format(new Date(alert.created_at), 'MMM d, HH:mm')}
                    </td>
                    <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-center gap-1">
                        {alert.status === 'open' && (
                          <button
                            onClick={() => handleAcknowledge(alert.alert_id)}
                            className="btn-secondary px-2 py-1 text-xs"
                          >
                            Ack
                          </button>
                        )}
                        {(alert.status === 'acknowledged' || alert.status === 'investigating') && (
                          <button
                            onClick={() => handleResolve(alert.alert_id)}
                            className="btn-primary px-2 py-1 text-xs"
                          >
                            Resolve
                          </button>
                        )}
                      </div>
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
            <span className="text-xs text-slate-500">Page {page} of {totalPages}</span>
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
      {selectedAlert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setSelectedAlert(null)}>
          <div className="fixed inset-0 bg-black/30" />
          <div
            className="relative z-10 w-full max-w-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <AlertNotification alert={selectedAlert} onAcknowledge={handleAcknowledge} />
            <div className="mt-3 flex justify-end gap-2">
              <button onClick={() => setSelectedAlert(null)} className="btn-secondary text-xs">Close</button>
              {selectedAlert.status === 'open' && (
                <button
                  onClick={() => { handleAcknowledge(selectedAlert.alert_id); setSelectedAlert(null); }}
                  className="btn-primary text-xs"
                >
                  Acknowledge
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
