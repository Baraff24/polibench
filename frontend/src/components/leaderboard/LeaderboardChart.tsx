import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { MultiMetricLeaderboardEntry } from '../../models'

export type LeaderboardChartMode = 'auto' | 'line' | 'bar'

type Props = {
  entries: MultiMetricLeaderboardEntry[]
  metrics: string[]
  mode?: LeaderboardChartMode
}

const METRIC_COLORS: Record<string, string> = {
  auc: '#0ab39c',
  logloss: '#f06548',
  'ndcg@10': '#564ab1',
  'recall@20': '#4bc8ef',
  'hit@10': '#f7b84b',
  rmse: '#f06548',
  mae: '#f7b84b',
}

function getColor(metric: string, index: number): string {
  if (METRIC_COLORS[metric]) return METRIC_COLORS[metric]
  const fallback = ['#564ab1', '#0ab39c', '#f7b84b', '#4bc8ef', '#f06548']
  return fallback[index % fallback.length]
}

function padDomain(min: number, max: number): [number, number] {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [0, 1]
  const span = Math.max(max - min, 0.0001)
  const pad = span * 0.12
  return [min - pad, max + pad]
}

export default function LeaderboardChart({ entries, metrics, mode = 'auto' }: Props) {
  if (entries.length === 0 || metrics.length === 0) return null

  const data = entries.map((e) => {
    const row: Record<string, string | number> = {
      model: e.model_name || 'Unknown',
    }
    for (const m of metrics) {
      const val = e.metrics[m]
      if (val !== undefined) {
        row[m] = Number(val.toFixed(4))
      }
    }
    return row
  })

  const hasCtrPair = metrics.includes('auc') && metrics.includes('logloss')
  const shouldRenderCtrLine = mode === 'line' ? hasCtrPair : mode === 'auto' && hasCtrPair

  if (shouldRenderCtrLine) {
    const sortedData = [...data].sort((a, b) => {
      const aAuc = typeof a.auc === 'number' ? a.auc : Number.NEGATIVE_INFINITY
      const bAuc = typeof b.auc === 'number' ? b.auc : Number.NEGATIVE_INFINITY
      return aAuc - bAuc
    })
    const aucValues = sortedData
      .map((d) => (typeof d.auc === 'number' ? d.auc : undefined))
      .filter((v): v is number => v !== undefined)
    const loglossValues = sortedData
      .map((d) => (typeof d.logloss === 'number' ? d.logloss : undefined))
      .filter((v): v is number => v !== undefined)
    const aucDomain =
      aucValues.length > 0 ? padDomain(Math.min(...aucValues), Math.max(...aucValues)) : [0, 1]
    const loglossDomain =
      loglossValues.length > 0
        ? padDomain(Math.min(...loglossValues), Math.max(...loglossValues))
        : [0, 1]

    return (
      <div className='leaderboard-chart'>
        <h3 className='leaderboard-chart__title'>Sorted Benchmarking Results by AUC</h3>
        <div className='leaderboard-chart__container'>
          <ResponsiveContainer width='100%' height={420}>
            <LineChart data={sortedData} margin={{ top: 16, right: 30, left: 6, bottom: 80 }}>
              <CartesianGrid strokeDasharray='3 3' stroke='rgba(255,255,255,0.10)' />
              <XAxis
                dataKey='model'
                interval={0}
                angle={-90}
                textAnchor='end'
                tick={{ fill: '#ced4da', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.10)' }}
                tickLine={false}
                height={84}
              />
              <YAxis
                yAxisId='left'
                domain={aucDomain}
                tick={{ fill: '#ced4da', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.10)' }}
                tickLine={false}
                label={{ value: 'AUC', angle: -90, position: 'insideLeft', fill: '#0ab39c' }}
              />
              <YAxis
                yAxisId='right'
                orientation='right'
                domain={loglossDomain}
                tick={{ fill: '#ced4da', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.10)' }}
                tickLine={false}
                label={{ value: 'Logloss', angle: 90, position: 'insideRight', fill: '#f06548' }}
              />
              <Tooltip
                formatter={(value, name) => [
                  typeof value === 'number' ? value.toFixed(4) : String(value ?? ''),
                  String(name).toUpperCase(),
                ]}
                contentStyle={{
                  background: '#1a1d27',
                  border: '1px solid rgba(255,255,255,0.12)',
                  borderRadius: '0.375rem',
                  color: '#ced4da',
                }}
              />
              <Legend wrapperStyle={{ color: '#ced4da', fontSize: 13 }} />
              <Line
                yAxisId='left'
                type='monotone'
                dataKey='auc'
                name='AUC'
                stroke='#0ab39c'
                strokeWidth={3}
                dot={{ r: 4, fill: '#0ab39c', stroke: '#0ab39c' }}
                activeDot={{ r: 6 }}
              />
              <Line
                yAxisId='right'
                type='monotone'
                dataKey='logloss'
                name='Logloss'
                stroke='#f06548'
                strokeWidth={3}
                dot={{ r: 4, fill: '#f06548', stroke: '#f06548' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    )
  }

  const shouldRenderGenericLine = mode === 'line'

  if (shouldRenderGenericLine) {
    const primaryMetric = metrics[0]
    const sortedData = [...data].sort((a, b) => {
      const aPrimary =
        typeof a[primaryMetric] === 'number'
          ? (a[primaryMetric] as number)
          : Number.NEGATIVE_INFINITY
      const bPrimary =
        typeof b[primaryMetric] === 'number'
          ? (b[primaryMetric] as number)
          : Number.NEGATIVE_INFINITY
      return aPrimary - bPrimary
    })
    return (
      <div className='leaderboard-chart'>
        <h3 className='leaderboard-chart__title'>
          Sorted Benchmarking Results by {primaryMetric.toUpperCase()}
        </h3>
        <div className='leaderboard-chart__container'>
          <ResponsiveContainer width='100%' height={420}>
            <LineChart data={sortedData} margin={{ top: 16, right: 24, left: 6, bottom: 80 }}>
              <CartesianGrid strokeDasharray='3 3' stroke='rgba(255,255,255,0.10)' />
              <XAxis
                dataKey='model'
                interval={0}
                angle={-90}
                textAnchor='end'
                tick={{ fill: '#ced4da', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.10)' }}
                tickLine={false}
                height={84}
              />
              <YAxis
                tick={{ fill: '#ced4da', fontSize: 12 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.10)' }}
                tickLine={false}
              />
              <Tooltip
                formatter={(value, name) => [
                  typeof value === 'number' ? value.toFixed(4) : String(value ?? ''),
                  String(name).toUpperCase(),
                ]}
                contentStyle={{
                  background: '#1a1d27',
                  border: '1px solid rgba(255,255,255,0.12)',
                  borderRadius: '0.375rem',
                  color: '#ced4da',
                }}
              />
              <Legend wrapperStyle={{ color: '#ced4da', fontSize: 13 }} />
              {metrics.map((m, i) => (
                <Line
                  key={m}
                  type='monotone'
                  dataKey={m}
                  name={m.toUpperCase()}
                  stroke={getColor(m, i)}
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: getColor(m, i), stroke: getColor(m, i) }}
                  activeDot={{ r: 5 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    )
  }

  return (
    <div className='leaderboard-chart'>
      <h3 className='leaderboard-chart__title'>Metrics Overview (Grouped Bars)</h3>
      <div className='leaderboard-chart__container'>
        <ResponsiveContainer width='100%' height={320}>
          <BarChart data={data} margin={{ top: 8, right: 24, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray='3 3' stroke='rgba(255,255,255,0.07)' />
            <XAxis
              dataKey='model'
              tick={{ fill: '#ced4da', fontSize: 12 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.07)' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: '#ced4da', fontSize: 12 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.07)' }}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: '#1a1d27',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: '0.375rem',
                color: '#ced4da',
              }}
            />
            <Legend wrapperStyle={{ color: '#ced4da', fontSize: 13 }} />
            {metrics.map((m, i) => (
              <Bar key={m} dataKey={m} fill={getColor(m, i)} radius={[4, 4, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
