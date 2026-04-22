import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router'
import { PageHeader, EmptyState, DataTable } from '../components'
import type { Column } from '../components'
import { datasetService, leaderboardService } from '../services'
import type {
  DatasetSummary,
  DatasetVersionSummary,
  MultiMetricLeaderboardEntry,
  Split,
} from '../models'
import LeaderboardChart, { type LeaderboardChartMode } from '../components/leaderboard/LeaderboardChart'

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

type SortOrder = 'asc' | 'desc'

export async function loader() {
  const datasets = await datasetService.getAll()
  return { datasets }
}

export default function Leaderboard() {
  const navigate = useNavigate()

  const [datasets, setDatasets] = useState<DatasetSummary[]>([])
  const [datasetUuid, setDatasetUuid] = useState('')
  const [datasetVersions, setDatasetVersions] = useState<DatasetVersionSummary[]>([])
  const [datasetVersionUuid, setDatasetVersionUuid] = useState('')
  const [split, setSplit] = useState<Split>('test')
  const [topN, setTopN] = useState(20)
  const [entries, setEntries] = useState<MultiMetricLeaderboardEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [metricNames, setMetricNames] = useState<string[]>([])
  const [sortBy, setSortBy] = useState('')
  const [chartMode, setChartMode] = useState<LeaderboardChartMode>('auto')
  const [tableSort, setTableSort] = useState<{ key: string; order: SortOrder } | null>(null)

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
    datasetService
      .getVersions(ds.uuid)
      .then((versions) => setDatasetVersions(versions))
      .catch(() => setDatasetVersions([]))
    setDatasetVersionUuid('')
    const preset = METRIC_PRESETS[ds.task] || METRIC_PRESETS['ranking']
    setMetricNames(preset.metrics)
    setSortBy(preset.sortBy)
    setTableSort(null)
  }

  // Fetch multi-metric leaderboard when filters change
  useEffect(() => {
    if (!datasetUuid || metricNames.length === 0 || !sortBy) return
    setLoading(true)
    leaderboardService
      .getMultiMetric(datasetUuid, metricNames, split, sortBy, topN, datasetVersionUuid || undefined)
      .then(setEntries)
      .catch(() => setEntries([]))
      .finally(() => setLoading(false))
  }, [datasetUuid, datasetVersionUuid, metricNames, split, sortBy, topN])

  function handleDatasetChange(uuid: string) {
    const ds = datasets.find((d) => d.uuid === uuid)
    if (ds) selectDataset(ds)
  }

  const firstEntry = entries.length > 0 ? entries[0] : null

  useEffect(() => {
    if (entries.length === 0) return
    const validKeys = new Set(['rank', 'model', 'running_steps', ...metricNames])
    if (tableSort && validKeys.has(tableSort.key)) return
    setTableSort({
      key: sortBy || 'rank',
      order: firstEntry?.directions[sortBy] === 'min' ? 'asc' : 'desc',
    })
  }, [entries, firstEntry, metricNames, sortBy, tableSort])

  function sortIndicator(key: string): string {
    if (!tableSort || tableSort.key !== key) return '↕'
    return tableSort.order === 'asc' ? '↑' : '↓'
  }

  function toggleSort(key: string) {
    setTableSort((prev) => {
      if (!prev || prev.key !== key) {
        if (key === 'rank' || key === 'model' || key === 'running_steps') {
          return { key, order: 'asc' }
        }
        return {
          key,
          order: firstEntry?.directions[key] === 'min' ? 'asc' : 'desc',
        }
      }
      return { key, order: prev.order === 'asc' ? 'desc' : 'asc' }
    })
  }

  function sortableHeader(label: string, key: string) {
    const active = tableSort?.key === key
    const nextOrder = !active || tableSort.order === 'desc' ? 'asc' : 'desc'
    return (
      <button
        type='button'
        className={`table__sort-btn${active ? ' table__sort-btn--active' : ''}`}
        onClick={() => toggleSort(key)}
        aria-label={`Sort by ${label} (${nextOrder})`}
      >
        <span>{label}</span>
        <span className='table__sort-indicator'>{sortIndicator(key)}</span>
      </button>
    )
  }

  const sortedEntries = useMemo(() => {
    if (!tableSort) return entries
    const rows = [...entries]
    const directionFactor = tableSort.order === 'asc' ? 1 : -1

    rows.sort((a, b) => {
      if (tableSort.key === 'rank') {
        const aRank = a.rank ?? Number.MAX_SAFE_INTEGER
        const bRank = b.rank ?? Number.MAX_SAFE_INTEGER
        return (aRank - bRank) * directionFactor
      }

      if (tableSort.key === 'model') {
        const aModel = (a.model_name || a.model_uuid).toLowerCase()
        const bModel = (b.model_name || b.model_uuid).toLowerCase()
        return aModel.localeCompare(bModel) * directionFactor
      }

      if (tableSort.key === 'running_steps') {
        const aRepo = a.repo_url || ''
        const bRepo = b.repo_url || ''
        const aHasRepo = aRepo !== ''
        const bHasRepo = bRepo !== ''
        if (aHasRepo !== bHasRepo) {
          return (Number(aHasRepo) - Number(bHasRepo)) * directionFactor
        }
        return aRepo.localeCompare(bRepo) * directionFactor
      }

      const aVal = a.metrics[tableSort.key]
      const bVal = b.metrics[tableSort.key]
      if (aVal === undefined && bVal === undefined) return 0
      if (aVal === undefined) return 1
      if (bVal === undefined) return -1
      return (aVal - bVal) * directionFactor
    })

    return rows
  }, [entries, tableSort])

  // Colonne dinamiche
  const columns: Column<MultiMetricLeaderboardEntry>[] = [
    {
      key: 'rank',
      header: sortableHeader('#', 'rank'),
      render: (_e, rowIndex) => <span className={rankClass(rowIndex + 1)}>{rowIndex + 1}</span>,
    },
    {
      key: 'model',
      header: sortableHeader('Model', 'model'),
      render: (e) => <span className='leaderboard-model'>{e.model_name || e.model_uuid}</span>,
    },
    // Una colonna per ogni metrica richiesta
    ...metricNames.map((m) => ({
      key: m,
      header: sortableHeader(m.toUpperCase() + directionArrow(firstEntry?.directions[m]), m),
      render: (e: MultiMetricLeaderboardEntry) => {
        const val = e.metrics[m]
        if (val === undefined) return '—'
        return val.toFixed(4)
      },
    })),
    {
      key: 'running_steps',
      header: sortableHeader('Running Steps', 'running_steps'),
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
                {ds.name}
              </option>
            ))}
          </select>
        </div>

        <div className='leaderboard-filters__field'>
          <label className='leaderboard-filters__label'>Version</label>
          <select
            className='leaderboard-filters__select'
            value={datasetVersionUuid}
            onChange={(e) => setDatasetVersionUuid(e.target.value)}
          >
            <option value=''>All versions</option>
            {datasetVersions.map((version) => (
              <option key={version.uuid} value={version.uuid}>
                v{version.version} ({version.status})
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

        <div className='leaderboard-filters__field'>
          <label className='leaderboard-filters__label'>Chart mode</label>
          <select
            className='leaderboard-filters__select'
            value={chartMode}
            onChange={(e) => setChartMode(e.target.value as LeaderboardChartMode)}
          >
            <option value='auto'>Auto</option>
            <option value='line'>Line</option>
            <option value='bar'>Bars</option>
          </select>
        </div>
      </div>

      {/* Chart */}
      {!loading && entries.length > 0 && (
        <LeaderboardChart entries={entries} metrics={metricNames} mode={chartMode} />
      )}

      {/* Results */}
      {loading && <p className='text-muted'>Loading...</p>}
      {!loading && entries.length === 0 && (
        <EmptyState title='No results' description='Try different filters.' />
      )}
      {!loading && entries.length > 0 && (
        <DataTable
          columns={columns}
          rows={sortedEntries}
          rowKey={(e) => e.experiment_uuid}
          onRowClick={(e) => navigate(`/experiments/${e.experiment_uuid}`)}
        />
      )}
    </div>
  )
}
