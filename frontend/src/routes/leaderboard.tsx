import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router'
import { PageHeader, EmptyState, DataTable } from '../components'
import type { Column } from '../components'
import { datasetService, leaderboardService } from '../services'
import type { DatasetSummary, LeaderboardEntry, Split } from '../models'

function rankClass(rank: number | null): string {
  if (rank === 1) return 'leaderboard-rank leaderboard-rank--gold'
  if (rank === 2) return 'leaderboard-rank leaderboard-rank--silver'
  if (rank === 3) return 'leaderboard-rank leaderboard-rank--bronze'
  return 'leaderboard-rank'
}

export async function loader() {
  const datasets = await datasetService.getAll()
  return { datasets }
}

export default function Leaderboard() {
  const navigate = useNavigate()

  const [datasets, setDatasets] = useState<DatasetSummary[]>([])
  const [datasetUuid, setDatasetUuid] = useState('')
  const [metric, setMetric] = useState('ndcg@10')
  const [split, setSplit] = useState<Split>('test')
  const [topN, setTopN] = useState(10)
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])
  const [loading, setLoading] = useState(false)

  // Load datasets on mount
  useEffect(() => {
    datasetService.getAll().then((ds) => {
      setDatasets(ds)
      if (ds.length > 0) {
        setDatasetUuid(ds[0].uuid)
      }
    })
  }, [])

  // Fetch leaderboard when filters change
  useEffect(() => {
    if (!datasetUuid || !metric) return
    setLoading(true)
    leaderboardService
      .get(datasetUuid, metric, split, topN)
      .then(setEntries)
      .catch(() => setEntries([]))
      .finally(() => setLoading(false))
  }, [datasetUuid, metric, split, topN])

  const columns: Column<LeaderboardEntry>[] = [
    {
      key: 'rank',
      header: '#',
      render: (e) => <span className={rankClass(e.rank)}>{e.rank}</span>,
    },
    { key: 'model', header: 'Model', render: (e) => e.model_name || e.model_uuid },
    { key: 'value', header: 'Value', render: (e) => e.value.toFixed(4) },
    { key: 'metric', header: 'Metric', render: (e) => e.metric },
    { key: 'direction', header: 'Direction', render: (e) => e.direction },
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
            onChange={(e) => setDatasetUuid(e.target.value)}
          >
            {datasets.map((ds) => (
              <option key={ds.uuid} value={ds.uuid}>
                {ds.name} v{ds.version}
              </option>
            ))}
          </select>
        </div>

        <div className='leaderboard-filters__field'>
          <label className='leaderboard-filters__label'>Metric</label>
          <input
            className='leaderboard-filters__input'
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
          />
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
