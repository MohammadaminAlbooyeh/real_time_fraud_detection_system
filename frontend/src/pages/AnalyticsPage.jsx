import { useState, useEffect, useCallback } from 'react'
import api from '../services/fraud_api'
import MetricsChart from '../components/MetricsChart'

const METRICS = [
  { value: 'transactions', label: 'Transactions' },
  { value: 'alerts', label: 'Alerts' },
  { value: 'fraud_score', label: 'Fraud Score' },
  { value: 'processing_time', label: 'Processing Time' },
]

const GRANULARITIES = [
  { value: '1m', label: '1 Minute' },
  { value: '5m', label: '5 Minutes' },
  { value: '15m', label: '15 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '1d', label: '1 Day' },
]

const CHART_COLORS = {
  transactions: '#3b82f6',
  alerts: '#ef4444',
  fraud_score: '#f59e0b',
  processing_time: '#8b5cf6',
}

export default function AnalyticsPage() {
  const [selectedMetric, setSelectedMetric] = useState('transactions')
  const [granularity, setGranularity] = useState('5m')
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [rules, setRules] = useState(null)
  const [summary, setSummary] = useState(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [tsData, rulesData, summaryData] = await Promise.all([
        api.getTimeSeries({ metric: selectedMetric, granularity }),
        api.getRules().catch(() => null),
        api.getMetricsSummary().catch(() => null),
      ])
      setData(tsData?.data || [])
      if (rulesData) setRules(rulesData)
      if (summaryData) setSummary(summaryData)
    } catch (err) {
      console.error('Failed to load analytics:', err)
    } finally {
      setLoading(false)
    }
  }, [selectedMetric, granularity])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Analytics</h1>
        <p className="mt-0.5 text-sm text-slate-500">Detailed metrics and performance data</p>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Metric</label>
          <select
            className="select-field w-40"
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value)}
          >
            {METRICS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Granularity</label>
          <select
            className="select-field w-32"
            value={granularity}
            onChange={(e) => setGranularity(e.target.value)}
          >
            {GRANULARITIES.map((g) => (
              <option key={g.value} value={g.value}>{g.label}</option>
            ))}
          </select>
        </div>
        <button onClick={fetchData} className="btn-secondary mt-5 text-xs" disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {/* Main Chart */}
      <MetricsChart
        title={`${METRICS.find((m) => m.value === selectedMetric)?.label} — ${GRANULARITIES.find((g) => g.value === granularity)?.label}`}
        data={data}
        lines={[{ dataKey: 'value', color: CHART_COLORS[selectedMetric] || '#3b82f6', name: selectedMetric }]}
        type={selectedMetric === 'processing_time' ? 'bar' : 'area'}
        height={400}
        loading={loading}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Rules Overview */}
        <div className="stat-card">
          <h3 className="mb-4 text-sm font-semibold text-slate-900">Fraud Detection Rules</h3>
          {!rules ? (
            <p className="py-8 text-center text-sm text-slate-400">No rule data available</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(rules).map(([name, rule]) => (
                <div key={name} className="flex items-center justify-between rounded-lg border border-slate-100 px-4 py-3">
                  <div className="flex items-center gap-3">
                    <span className={`inline-block h-2 w-2 rounded-full ${rule.enabled ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                    <span className="text-sm font-medium text-slate-800">{name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500">{rule.type || '-'}</span>
                    <span className={`badge ${rule.enabled ? 'badge-green' : 'badge-slate'}`}>
                      {rule.enabled ? 'Active' : 'Disabled'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Summary Stats */}
        <div className="stat-card">
          <h3 className="mb-4 text-sm font-semibold text-slate-900">Summary Statistics</h3>
          {!summary ? (
            <p className="py-8 text-center text-sm text-slate-400">No summary data available</p>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Transactions (24h)</p>
                  <p className="mt-1 text-lg font-bold text-slate-900">
                    {summary.transactions_last_24h?.toLocaleString() || '-'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Alerts (24h)</p>
                  <p className="mt-1 text-lg font-bold text-slate-900">
                    {summary.alerts_last_24h?.toLocaleString() || '-'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Fraud Rate</p>
                  <p className="mt-1 text-lg font-bold text-slate-900">
                    {summary.fraud_rate ? `${(summary.fraud_rate * 100).toFixed(2)}%` : '-'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Avg Processing</p>
                  <p className="mt-1 text-lg font-bold text-slate-900">
                    {summary.avg_processing_time_ms ? `${summary.avg_processing_time_ms.toFixed(1)}ms` : '-'}
                  </p>
                </div>
              </div>

              {summary.top_triggered_rules && summary.top_triggered_rules.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">Top Triggered Rules</p>
                  <div className="space-y-2">
                    {summary.top_triggered_rules.map((rule, i) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <span className="text-slate-700">{rule.rule || rule.name || `Rule ${i + 1}`}</span>
                        <span className="font-medium text-slate-900">{rule.count || 0}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
