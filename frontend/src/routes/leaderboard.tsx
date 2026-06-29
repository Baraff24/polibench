import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import { DataTable, EmptyState, PageHeader } from '../components'
import type { Column } from '../components'
import { datasetService, leaderboardService, mlModelService } from '../services'
import type {
  BestConfigurationResponse,
  DatasetSummary,
  DatasetVersionSummary,
  Direction,
  MLModelSummary,
  MultiMetricLeaderboardEntry,
  PipelineSummary,
  Split,
} from '../models'
import LeaderboardChart, { type LeaderboardChartMode } from '../components/leaderboard/LeaderboardChart'
import { useSnackBar } from '../contexts/snackbar'

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

function latexEscape(value: string): string {
  return value
    .replace(/\\/g, '\\textbackslash{}')
    .replace(/_/g, '\\_')
    .replace(/%/g, '\\%')
    .replace(/&/g, '\\&')
    .replace(/#/g, '\\#')
    .replace(/\$/g, '\\$')
    .replace(/\{/g, '\\{')
    .replace(/\}/g, '\\}')
    .replace(/~/g, '\\textasciitilde{}')
    .replace(/\^/g, '\\textasciicircum{}')
}

const METRIC_PRESETS: Record<string, { metrics: string[]; sortBy: string }> = {
  ctr: { metrics: ['auc', 'logloss'], sortBy: 'auc' },
  ranking: { metrics: ['ndcg@10', 'recall@20', 'hit@10'], sortBy: 'ndcg@10' },
  rating_prediction: { metrics: ['rmse', 'mae'], sortBy: 'rmse' },
}

type SortOrder = 'asc' | 'desc'
type LeaderboardViewMode = 'raw' | 'best_configuration'

type ColumnDef = {
  id: string
  label: string
  render: (entry: MultiMetricLeaderboardEntry, rowIndex: number) => string
}

const STORAGE_VISIBLE_COLUMNS_KEY = 'leaderboard.visibleColumns.v2'
const QUERY_TOP_N = 5000
const SHOW_HYPERPARAM_FILTERS = false

function formatHyperparamsLabel(hyperparams: Record<string, unknown>): string {
  const keys = Object.keys(hyperparams)
  if (keys.length === 0) return 'model only'
  return keys
    .sort((a, b) => a.localeCompare(b))
    .map((key) => `${key}=${String(hyperparams[key])}`)
    .join(', ')
}

export default function Leaderboard() {
  const navigate = useNavigate()
  const { showSnackBar } = useSnackBar()

  const [datasets, setDatasets] = useState<DatasetSummary[]>([])
  const [models, setModels] = useState<MLModelSummary[]>([])

  const [datasetUuid, setDatasetUuid] = useState('')
  const [datasetVersions, setDatasetVersions] = useState<DatasetVersionSummary[]>([])
  const [datasetVersionUuid, setDatasetVersionUuid] = useState('')
  const [pipelines, setPipelines] = useState<PipelineSummary[]>([])
  const [pipelineUuid, setPipelineUuid] = useState('')

  const [split, setSplit] = useState<Split>('test')
  const [entries, setEntries] = useState<MultiMetricLeaderboardEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [viewMode, setViewMode] = useState<LeaderboardViewMode>('raw')

  const [metricNames, setMetricNames] = useState<string[]>([])
  const [sortBy, setSortBy] = useState('')
  const [chartMode, setChartMode] = useState<LeaderboardChartMode>('auto')
  const [tableSort, setTableSort] = useState<{ key: string; order: SortOrder } | null>(null)

  const [selectedModelUuids, setSelectedModelUuids] = useState<string[]>([])
  const [selectedAuthorUuids, setSelectedAuthorUuids] = useState<string[]>([])

  const [hyperparamFilters, setHyperparamFilters] = useState<Record<string, string>>({})
  const [selectedHyperparamColumns, setSelectedHyperparamColumns] = useState<string[]>([])

  const [visibleColumns, setVisibleColumns] = useState<string[]>(() => {
    const raw = localStorage.getItem(STORAGE_VISIBLE_COLUMNS_KEY)
    if (!raw) {
      return ['rank', 'model', 'pipeline', 'author', 'run_name', 'status']
    }
    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) {
        return parsed.filter((item) => typeof item === 'string')
      }
      return ['rank', 'model', 'pipeline', 'author', 'run_name', 'status']
    } catch {
      return ['rank', 'model', 'pipeline', 'author', 'run_name', 'status']
    }
  })

  const [bestLoading, setBestLoading] = useState(false)
  const [bestResponse, setBestResponse] = useState<BestConfigurationResponse | null>(null)

  useEffect(() => {
    localStorage.setItem(STORAGE_VISIBLE_COLUMNS_KEY, JSON.stringify(visibleColumns))
  }, [visibleColumns])

  useEffect(() => {
    datasetService.getAll().then((loadedDatasets) => {
      setDatasets(loadedDatasets)
      if (loadedDatasets.length > 0) {
        selectDataset(loadedDatasets[0])
      }
    })
    mlModelService.getAll().then(setModels)
  }, [])

  function selectDataset(ds: DatasetSummary) {
    setDatasetUuid(ds.uuid)
    setDatasetVersionUuid('')
    setPipelineUuid('')
    setPipelines([])
    setSelectedAuthorUuids([])
    setSelectedModelUuids([])
    setHyperparamFilters({})
    setSelectedHyperparamColumns([])

    datasetService
      .getVersions(ds.uuid)
      .then((loadedVersions) => setDatasetVersions(loadedVersions))
      .catch(() => setDatasetVersions([]))

    const preset = METRIC_PRESETS[ds.task] || METRIC_PRESETS['ranking']
    setMetricNames(preset.metrics)
    setSortBy(preset.sortBy)
    setTableSort(null)
  }

  useEffect(() => {
    if (!datasetVersionUuid) {
      setPipelines([])
      setPipelineUuid('')
      return
    }
    datasetService
      .getVersionPipelines(datasetVersionUuid)
      .then((loadedPipelines) => {
        setPipelines(loadedPipelines)
        if (loadedPipelines.length > 0) {
          setPipelineUuid(loadedPipelines[0].uuid)
        } else {
          setPipelineUuid('')
        }
      })
      .catch(() => {
        setPipelines([])
        setPipelineUuid('')
      })
  }, [datasetVersionUuid])

  useEffect(() => {
    setViewMode('raw')
    setBestResponse(null)
  }, [
    datasetUuid,
    datasetVersionUuid,
    pipelineUuid,
    split,
    metricNames,
    sortBy,
    selectedModelUuids,
    selectedAuthorUuids,
  ])

  useEffect(() => {
    if (!datasetUuid || metricNames.length === 0 || !sortBy) return
    if (datasetVersionUuid && !pipelineUuid) {
      setEntries([])
      return
    }

    setLoading(true)
    leaderboardService
      .query({
        dataset_uuid: datasetUuid,
        dataset_version_uuid: datasetVersionUuid || undefined,
        pipeline_uuid: pipelineUuid || undefined,
        split,
        metrics: metricNames,
        sort_by: sortBy,
        top_n: QUERY_TOP_N,
        model_uuids: selectedModelUuids.length > 0 ? selectedModelUuids : undefined,
        author_uuids: selectedAuthorUuids.length > 0 ? selectedAuthorUuids : undefined,
      })
      .then((loadedEntries) => setEntries(loadedEntries))
      .catch(() => setEntries([]))
      .finally(() => setLoading(false))
  }, [
    datasetUuid,
    datasetVersionUuid,
    pipelineUuid,
    split,
    metricNames,
    sortBy,
    selectedModelUuids,
    selectedAuthorUuids,
  ])

  function handleDatasetChange(uuid: string) {
    const ds = datasets.find((d) => d.uuid === uuid)
    if (ds) selectDataset(ds)
  }

  const availableAuthors = useMemo(() => {
    const byId = new Map<string, { uuid: string; label: string }>()
    for (const entry of entries) {
      if (!entry.submitted_by_user_uuid) continue
      byId.set(entry.submitted_by_user_uuid, {
        uuid: entry.submitted_by_user_uuid,
        label:
          entry.submitted_by_display_name ||
          entry.submitted_by_email ||
          entry.submitted_by_user_uuid,
      })
    }
    return Array.from(byId.values()).sort((a, b) => a.label.localeCompare(b.label))
  }, [entries])

  const availableHyperparamKeys = useMemo(() => {
    const keys = new Set<string>()
    for (const entry of entries) {
      const config = entry.training_config || {}
      Object.keys(config).forEach((key) => keys.add(key))
    }
    return Array.from(keys).sort((a, b) => a.localeCompare(b))
  }, [entries])

  function sortIndicator(key: string): string {
    if (!tableSort || tableSort.key !== key) return '↕'
    return tableSort.order === 'asc' ? '↑' : '↓'
  }

  function toggleSort(key: string) {
    setTableSort((prev) => {
      if (!prev || prev.key !== key) {
        return { key, order: 'asc' }
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

  const bestConfigurationEntries = useMemo<MultiMetricLeaderboardEntry[]>(() => {
    if (!bestResponse || !bestResponse.best_group) return []
    const targetMetric = bestResponse.target_metric
    const pipelineCode = pipelines.find((pipeline) => pipeline.uuid === bestResponse.pipeline_uuid)?.code || null
    const group = bestResponse.best_group
    const trainingConfig = group.best_training_config || group.hyperparams
    const metrics =
      Object.keys(group.best_metrics).length > 0
        ? group.best_metrics
        : { [targetMetric]: group.best_value }
    const directions =
      Object.keys(group.directions).length > 0
        ? group.directions
        : { [targetMetric]: bestResponse.direction }

    return [
      {
        experiment_uuid: group.best_experiment_uuid || `agg-best-${group.model_uuid}`,
        model_uuid: group.model_uuid,
        model_name: group.model_name,
        dataset_uuid: bestResponse.dataset_uuid,
        dataset_version_uuid: bestResponse.dataset_version_uuid,
        pipeline_uuid: bestResponse.pipeline_uuid,
        pipeline_code: pipelineCode,
        submitted_by_user_uuid: group.submitted_by_user_uuid,
        submitted_by_display_name: group.submitted_by_display_name,
        submitted_by_email: group.submitted_by_email,
        training_config: trainingConfig,
        status: 'aggregated',
        run_name: group.best_run_name || formatHyperparamsLabel(trainingConfig),
        seed: null,
        created_at: null,
        split: bestResponse.split,
        metrics,
        directions,
        repo_url: null,
        rank: 1,
      },
    ]
  }, [bestResponse, pipelines])

  const activeMetricNames = useMemo(() => {
    if (viewMode === 'best_configuration' && bestResponse) {
      return bestResponse.metrics.length > 0 ? bestResponse.metrics : [bestResponse.target_metric]
    }
    return metricNames
  }, [viewMode, bestResponse, metricNames])

  const activeEntries = useMemo(() => {
    if (viewMode === 'best_configuration') {
      return bestConfigurationEntries
    }
    return entries
  }, [viewMode, bestConfigurationEntries, entries])

  const targetMetricDirection = useMemo<Direction>(() => {
    for (const entry of entries) {
      const direction = entry.directions[sortBy]
      if (direction) return direction
    }

    const normalizedMetric = sortBy.toLowerCase()
    if (
      normalizedMetric.includes('loss') ||
      normalizedMetric.includes('rmse') ||
      normalizedMetric.includes('mae')
    ) {
      return 'min'
    }
    return 'max'
  }, [entries, sortBy])

  const sortedEntries = useMemo(() => {
    if (!tableSort) return activeEntries
    const rows = [...activeEntries]
    const directionFactor = tableSort.order === 'asc' ? 1 : -1

    rows.sort((a, b) => {
      const key = tableSort.key
      if (key === 'rank') {
        const aRank = a.rank ?? Number.MAX_SAFE_INTEGER
        const bRank = b.rank ?? Number.MAX_SAFE_INTEGER
        return (aRank - bRank) * directionFactor
      }
      if (key === 'model') {
        return (a.model_name || a.model_uuid).localeCompare(b.model_name || b.model_uuid) * directionFactor
      }
      if (key === 'pipeline') {
        return (a.pipeline_code || '').localeCompare(b.pipeline_code || '') * directionFactor
      }
      if (key === 'author') {
        return (
          (a.submitted_by_display_name || a.submitted_by_email || '').localeCompare(
            b.submitted_by_display_name || b.submitted_by_email || '',
          ) * directionFactor
        )
      }
      if (key === 'run_name') {
        return (a.run_name || '').localeCompare(b.run_name || '') * directionFactor
      }
      if (key === 'status') {
        return (a.status || '').localeCompare(b.status || '') * directionFactor
      }
      if (key === 'seed') {
        return ((a.seed ?? -1) - (b.seed ?? -1)) * directionFactor
      }
      if (key === 'created_at') {
        const av = a.created_at ? new Date(a.created_at).getTime() : 0
        const bv = b.created_at ? new Date(b.created_at).getTime() : 0
        return (av - bv) * directionFactor
      }
      if (key.startsWith('metric:')) {
        const metricName = key.replace('metric:', '')
        const av = a.metrics[metricName]
        const bv = b.metrics[metricName]
        if (av === undefined && bv === undefined) return 0
        if (av === undefined) return 1
        if (bv === undefined) return -1
        return (av - bv) * directionFactor
      }
      if (key.startsWith('hp:')) {
        const hp = key.replace('hp:', '')
        const av = String((a.training_config || {})[hp] ?? '')
        const bv = String((b.training_config || {})[hp] ?? '')
        return av.localeCompare(bv) * directionFactor
      }
      return 0
    })

    return rows
  }, [activeEntries, tableSort])

  const firstEntry = activeEntries.length > 0 ? activeEntries[0] : null

  useEffect(() => {
    if (activeEntries.length === 0) return
    const validKeys = new Set(['rank', 'model', 'pipeline', 'author', 'run_name', 'status', 'seed', 'created_at'])
    activeMetricNames.forEach((metric) => validKeys.add(`metric:${metric}`))
    selectedHyperparamColumns.forEach((hp) => validKeys.add(`hp:${hp}`))

    if (tableSort && validKeys.has(tableSort.key)) return
    setTableSort({ key: 'rank', order: 'asc' })
  }, [activeEntries, activeMetricNames, selectedHyperparamColumns, tableSort])

  const columnDefs = useMemo<ColumnDef[]>(() => {
    const defs: ColumnDef[] = [
      { id: 'rank', label: '#', render: (_entry, rowIndex) => String(rowIndex + 1) },
      {
        id: 'model',
        label: 'Model',
        render: (entry) => entry.model_name || entry.model_uuid,
      },
      {
        id: 'pipeline',
        label: 'Pipeline',
        render: (entry) => entry.pipeline_code || '—',
      },
      {
        id: 'author',
        label: 'Author',
        render: (entry) =>
          entry.submitted_by_display_name || entry.submitted_by_email || '—',
      },
      {
        id: 'run_name',
        label: 'Run',
        render: (entry) => entry.run_name || '—',
      },
      {
        id: 'status',
        label: 'Status',
        render: (entry) => entry.status || '—',
      },
      {
        id: 'seed',
        label: 'Seed',
        render: (entry) => (entry.seed === null || entry.seed === undefined ? '—' : String(entry.seed)),
      },
      {
        id: 'created_at',
        label: 'Created',
        render: (entry) => (entry.created_at ? new Date(entry.created_at).toLocaleString() : '—'),
      },
    ]

    for (const metric of activeMetricNames) {
      defs.push({
        id: `metric:${metric}`,
        label: metric.toUpperCase() + directionArrow(firstEntry?.directions[metric]),
        render: (entry) => {
          const value = entry.metrics[metric]
          if (value === undefined) return '—'
          return value.toFixed(4)
        },
      })
    }

    for (const hp of selectedHyperparamColumns) {
      defs.push({
        id: `hp:${hp}`,
        label: `hp:${hp}`,
        render: (entry) => String((entry.training_config || {})[hp] ?? '—'),
      })
    }

    return defs
  }, [activeMetricNames, firstEntry, selectedHyperparamColumns])

  const activeColumnDefs = useMemo(() => {
    return columnDefs.filter((def) => visibleColumns.includes(def.id))
  }, [columnDefs, visibleColumns])

  const tableColumns = useMemo<Column<MultiMetricLeaderboardEntry>[]>(() => {
    return activeColumnDefs.map((def) => ({
      key: def.id,
      header: sortableHeader(def.label, def.id),
      render: (entry, rowIndex) => {
        if (def.id === 'rank') {
          return <span className={rankClass(rowIndex + 1)}>{rowIndex + 1}</span>
        }
        const value = def.render(entry, rowIndex)
        if (def.id === 'model') {
          return <span className='leaderboard-model'>{value}</span>
        }
        return value
      },
    }))
  }, [activeColumnDefs, tableSort])

  function toggleVisibleColumn(columnId: string) {
    setVisibleColumns((prev) => {
      if (prev.includes(columnId)) {
        return prev.filter((item) => item !== columnId)
      }
      return [...prev, columnId]
    })
  }

  function toggleMetric(metric: string) {
    setMetricNames((prev) => {
      if (prev.includes(metric)) {
        const next = prev.filter((item) => item !== metric)
        if (next.length === 0) return prev
        if (!next.includes(sortBy)) setSortBy(next[0])
        return next
      }
      return [...prev, metric]
    })
  }

  function toggleModelSelection(modelUuid: string) {
    setSelectedModelUuids((prev) => {
      if (prev.includes(modelUuid)) {
        return prev.filter((item) => item !== modelUuid)
      }
      return [...prev, modelUuid]
    })
  }

  function toggleAuthorSelection(authorUuid: string) {
    setSelectedAuthorUuids((prev) => {
      if (prev.includes(authorUuid)) {
        return prev.filter((item) => item !== authorUuid)
      }
      return [...prev, authorUuid]
    })
  }

  function toggleHyperparamColumnSelection(hyperparam: string) {
    setSelectedHyperparamColumns((prev) => {
      if (prev.includes(hyperparam)) {
        return prev.filter((item) => item !== hyperparam)
      }
      return [...prev, hyperparam]
    })
  }

  function toggleHyperparamFilterKey(key: string) {
    setHyperparamFilters((prev) => {
      if (!(key in prev)) {
        return { ...prev, [key]: '' }
      }
      const next = { ...prev }
      delete next[key]
      return next
    })
  }

  function updateHyperparamFilterValue(key: string, value: string) {
    setHyperparamFilters((prev) => ({ ...prev, [key]: value }))
  }

  async function exportLatex() {
    if (activeColumnDefs.length === 0 || sortedEntries.length === 0) {
      showSnackBar('Nothing to export.', 'error')
      return
    }

    const alignment = 'l'.repeat(activeColumnDefs.length)
    const header = activeColumnDefs.map((col) => latexEscape(col.label)).join(' & ')
    const bodyRows = sortedEntries.map((entry, rowIndex) => {
      return activeColumnDefs
        .map((columnDef) => latexEscape(columnDef.render(entry, rowIndex)))
        .join(' & ')
    })

    const latex = [
      `\\begin{tabular}{${alignment}}`,
      '\\hline',
      `${header} \\\\`,
      '\\hline',
      ...bodyRows.map((row) => `${row} \\\\`),
      '\\hline',
      '\\end{tabular}',
    ].join('\n')

    try {
      await navigator.clipboard.writeText(latex)
      showSnackBar('LaTeX copied to clipboard.', 'success')
    } catch {
      showSnackBar('Clipboard unavailable, downloading .tex instead.', 'warning')
    }

    const blob = new Blob([latex], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'leaderboard.tex'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  async function showBestConfiguration() {
    if (!datasetVersionUuid || !pipelineUuid) {
      showSnackBar('Select dataset version and pipeline first.', 'error')
      return
    }
    if (!sortBy) {
      showSnackBar('Select a target metric first.', 'error')
      return
    }

    setBestLoading(true)
    try {
      const response = await leaderboardService.getBestConfiguration({
        dataset_uuid: datasetUuid,
        dataset_version_uuid: datasetVersionUuid,
        pipeline_uuid: pipelineUuid,
        split,
        metrics: metricNames,
        target_metric: sortBy,
        direction: targetMetricDirection,
        group_by_hyperparams: [],
        model_uuids: selectedModelUuids.length > 0 ? selectedModelUuids : undefined,
        author_uuids: selectedAuthorUuids.length > 0 ? selectedAuthorUuids : undefined,
      })
      setBestResponse(response)
      setViewMode('best_configuration')
    } catch {
      showSnackBar('Unable to compute best configuration.', 'error')
    } finally {
      setBestLoading(false)
    }
  }

  return (
    <div className='page container'>
      <PageHeader title='Leaderboard' />

      <div className='leaderboard-filters'>
        <div className='leaderboard-filters__field'>
          <label className='leaderboard-filters__label'>Dataset</label>
          <select
            className='leaderboard-filters__select'
            value={datasetUuid}
            onChange={(e) => handleDatasetChange(e.target.value)}
          >
            {datasets.map((dataset) => (
              <option key={dataset.uuid} value={dataset.uuid}>
                {dataset.name}
              </option>
            ))}
          </select>
        </div>

        <div className='leaderboard-filters__field'>
          <label className='leaderboard-filters__label'>Version</label>
          <select
            className='leaderboard-filters__select'
            value={datasetVersionUuid}
            onChange={(e) => {
              setDatasetVersionUuid(e.target.value)
              setPipelineUuid('')
            }}
          >
            <option value=''>All versions</option>
            {datasetVersions.map((version) => (
              <option key={version.uuid} value={version.uuid}>
                v{version.version}
              </option>
            ))}
          </select>
        </div>

        <div className='leaderboard-filters__field'>
          <label className='leaderboard-filters__label'>Pipeline</label>
          <select
            className='leaderboard-filters__select'
            value={pipelineUuid}
            onChange={(e) => setPipelineUuid(e.target.value)}
            disabled={!datasetVersionUuid}
          >
            <option value=''>
              {datasetVersionUuid ? 'Select pipeline...' : 'Select version first...'}
            </option>
            {pipelines.map((pipeline) => (
              <option key={pipeline.uuid} value={pipeline.uuid}>
                {pipeline.code}
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
            {metricNames.map((metric) => (
              <option key={metric} value={metric}>
                {metric.toUpperCase()}
              </option>
            ))}
          </select>
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

      <section className='detail-section'>
        <h2 className='detail-section__title'>Table Controls</h2>

        <div className='leaderboard-filters'>
          <div className='leaderboard-filters__field'>
            <label className='leaderboard-filters__label'>Metrics</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {(METRIC_PRESETS[datasets.find((d) => d.uuid === datasetUuid)?.task || 'ranking']?.metrics ||
                metricNames
              ).map((metric) => (
                <label key={metric} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                  <input
                    type='checkbox'
                    checked={metricNames.includes(metric)}
                    onChange={() => toggleMetric(metric)}
                  />
                  <span>{metric}</span>
                </label>
              ))}
            </div>
          </div>

          <div className='leaderboard-filters__field'>
            <label className='leaderboard-filters__label'>Models</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                <input
                  type='checkbox'
                  checked={selectedModelUuids.length === 0}
                  onChange={() => setSelectedModelUuids([])}
                />
                <span>All models</span>
              </label>
              {models.map((model) => (
                <label
                  key={model.uuid}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <input
                    type='checkbox'
                    checked={selectedModelUuids.includes(model.uuid)}
                    onChange={() => toggleModelSelection(model.uuid)}
                  />
                  <span>{model.name}</span>
                </label>
              ))}
            </div>
          </div>

          <div className='leaderboard-filters__field'>
            <label className='leaderboard-filters__label'>Authors</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                <input
                  type='checkbox'
                  checked={selectedAuthorUuids.length === 0}
                  onChange={() => setSelectedAuthorUuids([])}
                />
                <span>All authors</span>
              </label>
              {availableAuthors.map((author) => (
                <label
                  key={author.uuid}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <input
                    type='checkbox'
                    checked={selectedAuthorUuids.includes(author.uuid)}
                    onChange={() => toggleAuthorSelection(author.uuid)}
                  />
                  <span>{author.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className='leaderboard-filters__field'>
            <label className='leaderboard-filters__label'>Hyperparam columns</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                <input
                  type='checkbox'
                  checked={selectedHyperparamColumns.length === 0}
                  onChange={() => setSelectedHyperparamColumns([])}
                />
                <span>No extra hyperparams columns</span>
              </label>
              {availableHyperparamKeys.map((key) => (
                <label
                  key={key}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <input
                    type='checkbox'
                    checked={selectedHyperparamColumns.includes(key)}
                    onChange={() => toggleHyperparamColumnSelection(key)}
                  />
                  <span>{key}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Filter by hyperparameters is intentionally disabled in the leaderboard UI. */}
        {SHOW_HYPERPARAM_FILTERS && (
          <div className='leaderboard-filters'>
            <div className='leaderboard-filters__field'>
              <label className='leaderboard-filters__label'>Filter by hyperparameters</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                  <input
                    type='checkbox'
                    checked={Object.keys(hyperparamFilters).length === 0}
                    onChange={() => setHyperparamFilters({})}
                  />
                  <span>All hyperparams values</span>
                </label>
                {availableHyperparamKeys.map((key) => (
                  <label
                    key={key}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
                  >
                    <input
                      type='checkbox'
                      checked={key in hyperparamFilters}
                      onChange={() => toggleHyperparamFilterKey(key)}
                    />
                    <span style={{ minWidth: '9rem' }}>{key}</span>
                    {key in hyperparamFilters && (
                      <input
                        className='leaderboard-filters__input'
                        placeholder='value'
                        value={hyperparamFilters[key]}
                        onChange={(event) =>
                          updateHyperparamFilterValue(key, event.target.value)
                        }
                        style={{ maxWidth: '14rem' }}
                      />
                    )}
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className='leaderboard-filters'>
          <div className='leaderboard-filters__field'>
            <label className='leaderboard-filters__label'>Visible columns</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {columnDefs.map((columnDef) => (
                <label key={columnDef.id} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                  <input
                    type='checkbox'
                    checked={visibleColumns.includes(columnDef.id)}
                    onChange={() => toggleVisibleColumn(columnDef.id)}
                  />
                  <span>{columnDef.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className='form__actions'>
          <button
            type='button'
            className='btn btn--outline'
            disabled={bestLoading}
            onClick={showBestConfiguration}
          >
            {bestLoading ? 'Computing...' : 'Show best configuration'}
          </button>
          {viewMode === 'best_configuration' && (
            <button
              type='button'
              className='btn btn--outline'
              onClick={() => setViewMode('raw')}
            >
              Show all configurations
            </button>
          )}
          <button type='button' className='btn btn--outline' onClick={exportLatex}>
            Export LaTeX
          </button>
        </div>
      </section>

      {loading && <p className='text-muted'>Loading...</p>}

      {!loading && (
        <section className='detail-section'>
          <h2 className='detail-section__title'>
            Current Results {viewMode === 'raw' ? '(Raw experiments)' : '(Best configuration / aggregated)'}
          </h2>

          {viewMode === 'best_configuration' && bestResponse && (
            <>
              <div className='detail-grid'>
                <div className='detail-field'>
                  <div className='detail-field__label'>Target metric</div>
                  <div className='detail-field__value'>{bestResponse.target_metric}</div>
                </div>
                <div className='detail-field'>
                  <div className='detail-field__label'>Direction</div>
                  <div className='detail-field__value'>{bestResponse.direction}</div>
                </div>
                <div className='detail-field'>
                  <div className='detail-field__label'>Aggregated by</div>
                  <div className='detail-field__value'>
                    model, ranked by {bestResponse.target_metric}
                  </div>
                </div>
                <div className='detail-field'>
                  <div className='detail-field__label'>Split</div>
                  <div className='detail-field__value'>{bestResponse.split}</div>
                </div>
              </div>

              {bestResponse.best_group && (
                <div className='detail-grid' style={{ marginTop: '0.75rem' }}>
                  <div className='detail-field'>
                    <div className='detail-field__label'>Best overall</div>
                    <div className='detail-field__value'>
                      {bestResponse.best_group.model_name || '—'} (BEST)
                    </div>
                  </div>
                  <div className='detail-field'>
                    <div className='detail-field__label'>Best value</div>
                    <div className='detail-field__value'>
                      {bestResponse.best_group.best_value.toFixed(6)}
                    </div>
                  </div>
                  <div className='detail-field'>
                    <div className='detail-field__label'>Best author</div>
                    <div className='detail-field__value'>
                      {bestResponse.best_group.submitted_by_display_name ||
                        bestResponse.best_group.submitted_by_email ||
                        '—'}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {activeEntries.length === 0 ? (
            <EmptyState
              title='No results'
              description={
                viewMode === 'best_configuration'
                  ? 'No groups matched the selected filters.'
                  : 'Try different filters.'
              }
            />
          ) : (
            <>
              <div className='detail-grid' style={{ marginTop: '0.75rem' }}>
                <div className='detail-field'>
                  <div className='detail-field__label'>Rows</div>
                  <div className='detail-field__value'>
                    {activeEntries.length}
                  </div>
                </div>
              </div>
              <div style={{ marginTop: '1rem' }}>
                <DataTable
                  columns={tableColumns}
                  rows={sortedEntries}
                  rowKey={(entry) => entry.experiment_uuid}
                  onRowClick={(entry) => {
                    if (entry.experiment_uuid.startsWith('agg-')) return
                    navigate(`/experiments/${entry.experiment_uuid}`)
                  }}
                />
              </div>
              <LeaderboardChart entries={sortedEntries} metrics={activeMetricNames} mode={chartMode} />
            </>
          )}
        </section>
      )}

    </div>
  )
}
