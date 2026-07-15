import { useState } from 'react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

const CHART_TYPES = {
  line: LineChart,
  bar: BarChart,
  area: AreaChart,
}

export default function MetricsChart({
  data = [],
  lines = [],
  type = 'line',
  title,
  height = 300,
  loading = false,
  onGranularityChange,
}) {
  const Chart = CHART_TYPES[type] || LineChart

  const renderShape = (entry, i) => {
    const { dataKey, color = '#3b82f6', strokeWidth = 2, name } = entry
    switch (type) {
      case 'bar':
        return <Bar key={dataKey} dataKey={dataKey} fill={color} name={name || dataKey} radius={[4, 4, 0, 0]} />
      case 'area':
        return (
          <Area
            key={dataKey}
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            fill={color}
            fillOpacity={0.1}
            strokeWidth={strokeWidth}
            name={name || dataKey}
          />
        )
      default:
        return (
          <Line
            key={dataKey}
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={strokeWidth}
            dot={false}
            activeDot={{ r: 4 }}
            name={name || dataKey}
          />
        )
    }
  }

  const formatXAxis = (val) => {
    if (!val) return ''
    try {
      const d = new Date(val)
      return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
    } catch {
      return val
    }
  }

  if (loading) {
    return (
      <div className="stat-card">
        {title && <h3 className="mb-4 text-sm font-semibold text-slate-900">{title}</h3>}
        <div className="flex items-center justify-center" style={{ height }}>
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
        </div>
      </div>
    )
  }

  return (
    <div className="stat-card">
      <div className="mb-4 flex items-center justify-between">
        {title && <h3 className="text-sm font-semibold text-slate-900">{title}</h3>}
        {onGranularityChange && (
          <select
            onChange={(e) => onGranularityChange(e.target.value)}
            className="select-field w-auto text-xs"
            defaultValue="5m"
          >
            <option value="1m">1 min</option>
            <option value="5m">5 min</option>
            <option value="15m">15 min</option>
            <option value="1h">1 hour</option>
            <option value="1d">1 day</option>
          </select>
        )}
      </div>

      {data.length === 0 ? (
        <div className="flex items-center justify-center text-sm text-slate-400" style={{ height }}>
          No data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={height}>
          <Chart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={formatXAxis}
              stroke="#94a3b8"
              fontSize={11}
              tickLine={false}
            />
            <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{
                background: '#fff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              labelFormatter={(val) => {
                try {
                  return new Date(val).toLocaleString()
                } catch {
                  return val
                }
              }}
            />
            {lines.length > 1 && <Legend />}
            {lines.map((entry, i) => renderShape(entry, i))}
          </Chart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
