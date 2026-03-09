import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router'
import { PageHeader, EmptyState, DataTable } from '../components'
import type { Column } from '../components'
import { datasetService, leaderboardService } from '../services'
import type { DatasetSummary, MultiMetricLeaderboardEntry, Split } from '../models'
import LeaderboardChart from '../components/leaderboard/LeaderboardChart'

function rankClass(rank: number | null): string {
  if (rank === 1) return 'leaderboard-rank leaderboard-rank--gold'
  if (rank === 2) return 'leaderboard-rank leaderboard-rank--silver'
  if (rank === 3) return 'leaderboard-rank leaderboard-rank--bronze'
  return 'leaderboard-rank'
}

function directionArrow(direction: string | undefined): string {
  if (direction === 'max') return ' ↑'
  if (direction === 'min') return ' ↓'
  return ''
}

// Preset metriche per task type
const METRIC_PRESETS: Record<string, { metrics: string[]; sortBy: string }> = {
  ctr: { metrics: ['auc', 'logloss'], sortBy: 'auc' },
  ranking: { metrics: ['ndcg@10', 'recall@20', 'hit@10'], sortBy: 'ndcg@10' },
  rating_prediction: { metrics: ['rmse', 'mae'], sortBy: 'rmse' },
}

export async function loader() {
  const datasets = await datasetService.getAll()
  return { datasets }
}

export default function Leaderboard() {
  const navigate = useNavigate()

  const [datasets, setDatasets] = useState<DatasetSummary[]>([])
  const [datasetUuid, setDatasetUuid] = useState('')
  const [split, setSplit] = useState<Split>('test')
  const [topN, setTopN] = useState(20)
  const [entries, setEntries] = useState<MultiMetricLeaderboardEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [metricNames, setMetricNames] = useState<string[]>([])
  const [sortBy, setSortBy] = useState('')

  // Load datasets on mount
  useEffect(() => {
    datasetService.getAll().then((ds) => {
      setDatasets(ds)
      if (ds.length > 0) {
        selectDataset(ds[0])
      }
    })
  }, [])

  function selectDataset(ds: DatasetSummary) {
    setDatasetUuid(ds.uuid)
    const preset = METRIC_PRESETS[ds.task] || METRIC_PRESETS['ranking']
    setMetricNames(preset.metrics)
    setSortBy(preset.sortBy)
  }

  // Fetch multi-metric leaderboard when filters change
  useEffect(() => {
    if (!datasetUuid || metricNames.length === 0 || !sortBy) return
    setLoading(true)
    leaderboardService
      .getMultiMetric(datasetUuid, metricNames, split, sortBy, topN)
      .then(setEntries)
      .catch(() => setEntries([]))
      .finally(() => setLoading(false))
  }, [datasetUuid, metricNames, split, sortBy, topN])

  function handleDatasetChange(uuid: string) {
    const ds = datasets.find((d) => d.uuid === uuid)
    if (ds) selectDataset(ds)
  }

  // Direzioni per le intestazioni colonna
  const firstEntry = entries.length > 0 ? entries[0] : null

  // Colonne dinamiche
  const columns: Column<MultiMetricLeaderboardEntry>[] = [
    {
      key: 'rank',
      header: '#',
      render: (e) => <span className={rankClass(e.rank)}>{e.rank}</span>,
    },
    {
      key: 'model',
      header: 'Model',
      render: (e) => <span className='leaderboard-model'>{e.model_name || e.model_uuid}</span>,
    },
    // Una colonna per ogni metrica richiesta
    ...metricNames.map((m) => ({
      key: m,
      header: m.toUpperCase() + directionArrow(firstEntry?.directions[m]),
      render: (e: MultiMetricLeaderboardEntry) => {
        const val = e.metrics[m]
        if (val === undefined) return '—'
        return val.toFixed(4)
      },
    })),
    {
      key: 'running_steps',
      header: 'Running Steps',
      render: (e) =>
        e.repo_url ? (
          <a
            className='leaderboard-link'
            href={e.repo_url}
            target='_blank'
            rel='noopener noreferrer'
            onClick={(ev) => ev.stopPropagation()}
          >
            View on GitHub
          </a>
        ) : (
          <span className='text-muted'>—</span>
        ),
    },
  ]

  return (
    <div className='page container'>
      <PageHeader title='Leaderboard' />

      {/* Filters */}
      <div className='leaderboard-filters'>
        <div className='leaderboard-filters__field'>
          <label className='leaderboard-filters__label'>Dataset</label>
          <select
            className='leaderboard-filters__select'
            value={datasetUuid}
            onChange={(e) => handleDatasetChange(e.target.value)}
          >
            {datasets.map((ds) => (
              <option key={ds.uuid} value={ds.uuid}>
                {ds.name} v{ds.version}
              </option>
            ))}
          </select>
        </div>

        <div className='leaderboard-filters__field'>
          <label className='leaderboard-filters__label'>Split</label>
          <select
            className='leaderboard-filters__select'
            value={split}
            onChange={(e) => setSplit(e.target.value as Split)}
          >
            <option value='test'>test</option>
            <option value='validation'>validation</option>
          </select>
        </div>

        <div className='leaderboard-filters__field'>
          <label className='leaderboard-filters__label'>Sort by</label>
          <select
            className='leaderboard-filters__select'
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            {metricNames.map((m) => (
              <option key={m} value={m}>
                {m.toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        <div className='leaderboard-filters__field'>
          <label className='leaderboard-filters__label'>Top N</label>
          <input
            className='leaderboard-filters__input'
            type='number'
            min={1}
            max={100}
            value={topN}
            onChange={(e) => setTopN(Number(e.target.value))}
          />
        </div>
      </div>

      {/* Chart */}
      {!loading && entries.length > 0 && (
        <LeaderboardChart entries={entries} metrics={metricNames} />
      )}

      {/* Results */}
      {loading && <p className='text-muted'>Loading...</p>}
      {!loading && entries.length === 0 && (
        <EmptyState title='No results' description='Try different filters.' />
      )}
      {!loading && entries.length > 0 && (
        <DataTable
          columns={columns}
          rows={entries}
          rowKey={(e) => e.experiment_uuid}
          onRowClick={(e) => navigate(`/experiments/${e.experiment_uuid}`)}
        />
      )}
    </div>
  )
}
