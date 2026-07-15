import { useState, useEffect, useCallback } from 'react'
import api from '../services/fraud_api'
import useWebSocket from '../hooks/useWebSocket'
import MetricCard from '../components/MetricCard'
import MetricsChart from '../components/MetricsChart'
import TransactionCard from '../components/TransactionCard'
import AlertNotification from '../components/AlertNotification'

export default function DashboardPage() {
  const [summary, setSummary] = useState(null)
  const [timeseries, setTimeseries] = useState([])
  const [recentTx, setRecentTx] = useState([])
  const [recentAlerts, setRecentAlerts] = useState([])
  const [liveFeed, setLiveFeed] = useState([])
  const [loading, setLoading] = useState(true)
  const [granularity, setGranularity] = useState('5m')

  const fetchData = useCallback(async () => {
    try {
      const [summaryData, tsData, txData, alertData] = await Promise.all([
        api.getMetricsSummary(),
        api.getTimeSeries({ metric: 'transactions', granularity }),
        api.listTransactions({ page_size: 5 }),
        api.listAlerts({ page_size: 5 }),
      ])
      setSummary(summaryData)
      setTimeseries(tsData?.data || [])
      setRecentTx(txData?.transactions || [])
      setRecentAlerts(alertData?.alerts || [])
    } catch (err) {
      console.error('Failed to load dashboard:', err)
    } finally {
      setLoading(false)
    }
  }, [granularity])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 15000)
    return () => clearInterval(interval)
  }, [fetchData])

  useWebSocket('transactions', (msg) => {
    if (msg.type === 'transaction' && msg.data) {
      setLiveFeed((prev) => [msg.data, ...prev].slice(0, 20))
    }
  })

  const formatNumber = (n) => {
    if (n === undefined || n === null) return '-'
    return n.toLocaleString()
  }

  const formatPct = (n) => {
    if (n === undefined || n === null) return '-'
    return `${(n * 100).toFixed(2)}%`
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Dashboard</h1>
          <p className="mt-0.5 text-sm text-slate-500">Real-time fraud detection overview</p>
        </div>
        <button onClick={fetchData} className="btn-secondary text-xs" disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {/* Metric Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Total Transactions"
          value={formatNumber(summary?.total_transactions)}
          sublabel="Last 24 hours"
          trend={5}
          color="blue"
          icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
            </svg>
          }
        />
        <MetricCard
          label="Total Alerts"
          value={formatNumber(summary?.total_alerts)}
          sublabel="Active alerts"
          trend={-3}
          color="red"
          icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
            </svg>
          }
        />
        <MetricCard
          label="Fraud Rate"
          value={formatPct(summary?.fraud_rate)}
          sublabel="Of total transactions"
          trend={-1.2}
          color="amber"
          icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          }
        />
        <MetricCard
          label="Avg Fraud Score"
          value={summary?.avg_fraud_score?.toFixed(3) || '-'}
          sublabel="Across all transactions"
          color="purple"
          icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
            </svg>
          }
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Chart */}
        <div className="lg:col-span-2">
          <MetricsChart
            title="Transaction Volume"
            data={timeseries}
            lines={[{ dataKey: 'value', color: '#3b82f6', name: 'Transactions' }]}
            type="area"
            loading={loading}
            onGranularityChange={setGranularity}
          />
        </div>

        {/* Alerts by Severity */}
        <div className="stat-card">
          <h3 className="mb-4 text-sm font-semibold text-slate-900">Alerts by Severity</h3>
          {loading ? (
            <div className="flex h-40 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
            </div>
          ) : summary?.alerts_by_severity ? (
            <div className="space-y-3">
              {Object.entries(summary.alerts_by_severity).map(([severity, count]) => {
                const total = Object.values(summary.alerts_by_severity).reduce((a, b) => a + b, 0)
                const pct = total > 0 ? (count / total) * 100 : 0
                const colors = {
                  critical: 'bg-red-500',
                  high: 'bg-orange-500',
                  medium: 'bg-amber-500',
                  low: 'bg-blue-500',
                }
                return (
                  <div key={severity}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="font-medium capitalize text-slate-700">{severity}</span>
                      <span className="text-slate-500">{count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100">
                      <div
                        className={`h-2 rounded-full transition-all ${colors[severity] || 'bg-slate-400'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-slate-400">No alert data</p>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Transactions */}
        <div className="stat-card">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Recent Transactions</h3>
            <a href="/transactions" className="text-xs font-medium text-blue-600 hover:text-blue-700">
              View all
            </a>
          </div>
          <div className="space-y-2">
            {loading ? (
              <p className="py-8 text-center text-sm text-slate-400">Loading...</p>
            ) : recentTx.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-400">No transactions yet</p>
            ) : (
              recentTx.map((tx) => <TransactionCard key={tx.transaction_id} transaction={tx} />)
            )}
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="stat-card">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Recent Alerts</h3>
            <a href="/alerts" className="text-xs font-medium text-blue-600 hover:text-blue-700">
              View all
            </a>
          </div>
          <div className="space-y-3">
            {loading ? (
              <p className="py-8 text-center text-sm text-slate-400">Loading...</p>
            ) : recentAlerts.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-400">No alerts yet</p>
            ) : (
              recentAlerts.map((alert) => (
                <AlertNotification key={alert.alert_id} alert={alert} />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Live Feed */}
      <div className="stat-card">
        <h3 className="mb-4 text-sm font-semibold text-slate-900">
          Live Transaction Feed
          <span className="ml-2 inline-block h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
        </h3>
        <div className="max-h-64 space-y-2 overflow-y-auto">
          {liveFeed.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-400">
              Waiting for transactions...
            </p>
          ) : (
            liveFeed.map((tx, i) => (
              <TransactionCard key={tx.transaction_id || i} transaction={tx} />
            ))
          )}
        </div>
      </div>
    </div>
  )
}
