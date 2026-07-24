const API_BASE = '/api/v1'
const WS_BASE = 'ws://' + window.location.host + '/api/v1'

class FraudApiService {
  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`
    const config = {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    }
    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body)
    }
    try {
      const res = await fetch(url, config)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      return res.json()
    } catch (err) {
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        throw new Error('Cannot connect to backend server')
      }
      throw err
    }
  }

  getHealth() {
    return this.request('/health')
  }

  submitTransaction(data) {
    return this.request('/transactions', { method: 'POST', body: data })
  }

  getTransaction(id) {
    return this.request(`/transactions/${id}`)
  }

  listTransactions(filters = {}) {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.set(k, v)
    })
    const qs = params.toString()
    return this.request(`/transactions${qs ? '?' + qs : ''}`)
  }

  submitBatch(transactions) {
    return this.request('/transactions/batch', { method: 'POST', body: transactions })
  }

  listAlerts(filters = {}) {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.set(k, v)
    })
    const qs = params.toString()
    return this.request(`/alerts${qs ? '?' + qs : ''}`)
  }

  getAlert(id) {
    return this.request(`/alerts/${id}`)
  }

  acknowledgeAlert(id, data) {
    return this.request(`/alerts/${id}/acknowledge`, { method: 'POST', body: data })
  }

  updateAlert(id, data) {
    return this.request(`/alerts/${id}`, { method: 'PATCH', body: data })
  }

  getMetricsSummary() {
    return this.request('/metrics/summary')
  }

  getTimeSeries(params) {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') qs.set(k, v)
    })
    return this.request(`/metrics/timeseries?${qs.toString()}`)
  }

  getRealtimeStatus() {
    return this.request('/metrics/realtime/status')
  }

  getRules() {
    return this.request('/rules')
  }

  createWebSocket(channel) {
    const url = `${WS_BASE}/ws/${channel}`
    return new WebSocket(url)
  }
}

const api = new FraudApiService()
export default api
