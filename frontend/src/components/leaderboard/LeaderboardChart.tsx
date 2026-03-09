import {
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

type Props = {
  entries: MultiMetricLeaderboardEntry[]
  metrics: string[]
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

export default function LeaderboardChart({ entries, metrics }: Props) {
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

  return (
    <div className='leaderboard-chart'>
      <h3 className='leaderboard-chart__title'>Metrics Overview</h3>
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
