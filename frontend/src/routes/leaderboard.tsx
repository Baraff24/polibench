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

function parseHyperparamFilterValue(raw: string): string | number | boolean {
  const normalized = raw.trim()
  if (normalized.toLowerCase() === 'true') return true
  if (normalized.toLowerCase() === 'false') return false
  if (normalized !== '' && !Number.isNaN(Number(normalized))) return Number(normalized)
  return normalized
}

const METRIC_PRESETS: Record<string, { metrics: string[]; sortBy: string }> = {
  ctr: { metrics: ['auc', 'logloss'], sortBy: 'auc' },
  ranking: { metrics: ['ndcg@10', 'recall@20', 'hit@10'], sortBy: 'ndcg@10' },
  rating_prediction: { metrics: ['rmse', 'mae'], sortBy: 'rmse' },
}

type SortOrder = 'asc' | 'desc'

type ColumnDef = {
  id: string
  label: string
  render: (entry: MultiMetricLeaderboardEntry, rowIndex: number) => string
}

const STORAGE_VISIBLE_COLUMNS_KEY = 'leaderboard.visibleColumns.v2'

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
  const [topN, setTopN] = useState(20)
  const [entries, setEntries] = useState<MultiMetricLeaderboardEntry[]>([])
  const [loading, setLoading] = useState(false)

  const [metricNames, setMetricNames] = useState<string[]>([])
  const [sortBy, setSortBy] = useState('')
  const [chartMode, setChartMode] = useState<LeaderboardChartMode>('auto')
  const [tableSort, setTableSort] = useState<{ key: string; order: SortOrder } | null>(null)

  const [selectedModelUuids, setSelectedModelUuids] = useState<string[]>([])
  const [selectedAuthorUuids, setSelectedAuthorUuids] = useState<string[]>([])

  const [hyperparamFilters, setHyperparamFilters] = useState<Record<string, string>>({})
  const [hyperparamFilterKey, setHyperparamFilterKey] = useState('')
  const [hyperparamFilterValue, setHyperparamFilterValue] = useState('')

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

  const [bestModalOpen, setBestModalOpen] = useState(false)
  const [bestDirection, setBestDirection] = useState<Direction>('max')
  const [bestGroupByInput, setBestGroupByInput] = useState('embedding_dim,learning_rate,batch_size')
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

  const queryHyperparamFilters = useMemo(() => {
    const out: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(hyperparamFilters)) {
      if (!key.trim() || !value.trim()) continue
      out[key] = parseHyperparamFilterValue(value)
    }
    return out
  }, [hyperparamFilters])

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
        top_n: topN,
        model_uuids: selectedModelUuids.length > 0 ? selectedModelUuids : undefined,
        author_uuids: selectedAuthorUuids.length > 0 ? selectedAuthorUuids : undefined,
        hyperparam_filters:
          Object.keys(queryHyperparamFilters).length > 0 ? queryHyperparamFilters : undefined,
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
    topN,
    selectedModelUuids,
    selectedAuthorUuids,
    queryHyperparamFilters,
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

  const firstEntry = entries.length > 0 ? entries[0] : null

  useEffect(() => {
    if (entries.length === 0) return
    const validKeys = new Set(['rank', 'model', 'pipeline', 'author', 'run_name', 'status', 'seed', 'created_at'])
    metricNames.forEach((metric) => validKeys.add(`metric:${metric}`))
    selectedHyperparamColumns.forEach((hp) => validKeys.add(`hp:${hp}`))

    if (tableSort && validKeys.has(tableSort.key)) return
    setTableSort({ key: 'rank', order: 'asc' })
  }, [entries, metricNames, selectedHyperparamColumns, tableSort])

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

  const sortedEntries = useMemo(() => {
    if (!tableSort) return entries
    const rows = [...entries]
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
  }, [entries, tableSort])

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

    for (const metric of metricNames) {
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
  }, [metricNames, firstEntry, selectedHyperparamColumns])

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

  function addHyperparamFilter() {
    const key = hyperparamFilterKey.trim()
    const value = hyperparamFilterValue.trim()
    if (!key || !value) {
      showSnackBar('Hyperparam key and value are required.', 'error')
      return
    }
    setHyperparamFilters((prev) => ({ ...prev, [key]: value }))
    setHyperparamFilterKey('')
    setHyperparamFilterValue('')
  }

  function removeHyperparamFilter(key: string) {
    setHyperparamFilters((prev) => {
      const next = { ...prev }
      delete next[key]
      return next
    })
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

    const groupBy = bestGroupByInput
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)

    setBestLoading(true)
    try {
      const response = await leaderboardService.getBestConfiguration({
        dataset_uuid: datasetUuid,
        dataset_version_uuid: datasetVersionUuid,
        pipeline_uuid: pipelineUuid,
        split,
        target_metric: sortBy,
        direction: bestDirection,
        group_by_hyperparams: groupBy,
        model_uuids: selectedModelUuids.length > 0 ? selectedModelUuids : undefined,
        author_uuids: selectedAuthorUuids.length > 0 ? selectedAuthorUuids : undefined,
        hyperparam_filters:
          Object.keys(queryHyperparamFilters).length > 0 ? queryHyperparamFilters : undefined,
      })
      setBestResponse(response)
      setBestModalOpen(true)
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
          <label className='leaderboard-filters__label'>Top N</label>
          <input
            className='leaderboard-filters__input'
            type='number'
            min={1}
            max={200}
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
            <select
              multiple
              className='leaderboard-filters__select'
              value={selectedModelUuids}
              onChange={(e) => {
                const values = Array.from(e.target.selectedOptions).map((opt) => opt.value)
                setSelectedModelUuids(values)
              }}
              style={{ minHeight: '7rem' }}
            >
              {models.map((model) => (
                <option key={model.uuid} value={model.uuid}>
                  {model.name}
                </option>
              ))}
            </select>
          </div>

          <div className='leaderboard-filters__field'>
            <label className='leaderboard-filters__label'>Authors</label>
            <select
              multiple
              className='leaderboard-filters__select'
              value={selectedAuthorUuids}
              onChange={(e) => {
                const values = Array.from(e.target.selectedOptions).map((opt) => opt.value)
                setSelectedAuthorUuids(values)
              }}
              style={{ minHeight: '7rem' }}
            >
              {availableAuthors.map((author) => (
                <option key={author.uuid} value={author.uuid}>
                  {author.label}
                </option>
              ))}
            </select>
          </div>

          <div className='leaderboard-filters__field'>
            <label className='leaderboard-filters__label'>Hyperparam columns</label>
            <select
              multiple
              className='leaderboard-filters__select'
              value={selectedHyperparamColumns}
              onChange={(e) => {
                const values = Array.from(e.target.selectedOptions).map((opt) => opt.value)
                setSelectedHyperparamColumns(values)
              }}
              style={{ minHeight: '7rem' }}
            >
              {availableHyperparamKeys.map((key) => (
                <option key={key} value={key}>
                  {key}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className='leaderboard-filters'>
          <div className='leaderboard-filters__field'>
            <label className='leaderboard-filters__label'>Add hyperparam filter</label>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <input
                className='leaderboard-filters__input'
                placeholder='key (e.g. embedding_dim)'
                value={hyperparamFilterKey}
                onChange={(e) => setHyperparamFilterKey(e.target.value)}
              />
              <input
                className='leaderboard-filters__input'
                placeholder='value (e.g. 64)'
                value={hyperparamFilterValue}
                onChange={(e) => setHyperparamFilterValue(e.target.value)}
              />
              <button type='button' className='btn btn--outline' onClick={addHyperparamFilter}>
                Add filter
              </button>
            </div>
            {Object.keys(hyperparamFilters).length > 0 && (
              <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {Object.entries(hyperparamFilters).map(([key, value]) => (
                  <button
                    key={key}
                    type='button'
                    className='btn btn--outline btn--sm'
                    onClick={() => removeHyperparamFilter(key)}
                  >
                    {key}={value} ×
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

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
          <button type='button' className='btn btn--outline' onClick={showBestConfiguration} disabled={bestLoading}>
            {bestLoading ? 'Computing...' : 'Show best configuration'}
          </button>
          <button type='button' className='btn btn--outline' onClick={exportLatex}>
            Export LaTeX
          </button>
        </div>
      </section>

      {loading && <p className='text-muted'>Loading...</p>}
      {!loading && entries.length === 0 && (
        <EmptyState title='No results' description='Try different filters.' />
      )}
      {!loading && entries.length > 0 && (
        <DataTable
          columns={tableColumns}
          rows={sortedEntries}
          rowKey={(entry) => entry.experiment_uuid}
          onRowClick={(entry) => navigate(`/experiments/${entry.experiment_uuid}`)}
        />
      )}

      {!loading && entries.length > 0 && (
        <LeaderboardChart entries={sortedEntries} metrics={metricNames} mode={chartMode} />
      )}

      {bestModalOpen && bestResponse && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(12, 16, 31, 0.58)',
            zIndex: 2000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem',
          }}
          onClick={() => setBestModalOpen(false)}
        >
          <div
            className='detail-section'
            style={{ width: 'min(920px, 100%)', maxHeight: '85vh', overflow: 'auto' }}
            onClick={(event) => event.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 className='detail-section__title'>Best Configuration</h2>
              <button type='button' className='btn btn--outline btn--sm' onClick={() => setBestModalOpen(false)}>
                Close
              </button>
            </div>

            <div className='detail-grid'>
              <div className='detail-field'>
                <div className='detail-field__label'>Target metric</div>
                <div className='detail-field__value'>{bestResponse.target_metric}</div>
              </div>
              <div className='detail-field'>
                <div className='detail-field__label'>Split</div>
                <div className='detail-field__value'>{bestResponse.split}</div>
              </div>
              <div className='detail-field'>
                <div className='detail-field__label'>Direction</div>
                <div className='detail-field__value'>{bestResponse.direction}</div>
              </div>
              <div className='detail-field'>
                <div className='detail-field__label'>Grouped by</div>
                <div className='detail-field__value'>
                  {bestResponse.group_by_hyperparams.join(', ') || 'model only'}
                </div>
              </div>
            </div>

            {bestResponse.best_group ? (
              <section className='detail-section'>
                <h3 className='detail-section__title'>Best Group</h3>
                <div className='detail-grid'>
                  <div className='detail-field'>
                    <div className='detail-field__label'>Model</div>
                    <div className='detail-field__value'>{bestResponse.best_group.model_name || '—'}</div>
                  </div>
                  <div className='detail-field'>
                    <div className='detail-field__label'>Author</div>
                    <div className='detail-field__value'>
                      {bestResponse.best_group.submitted_by_display_name ||
                        bestResponse.best_group.submitted_by_email ||
                        '—'}
                    </div>
                  </div>
                  <div className='detail-field'>
                    <div className='detail-field__label'>Best value</div>
                    <div className='detail-field__value'>{bestResponse.best_group.best_value.toFixed(6)}</div>
                  </div>
                  <div className='detail-field'>
                    <div className='detail-field__label'>Mean value</div>
                    <div className='detail-field__value'>{bestResponse.best_group.mean_value.toFixed(6)}</div>
                  </div>
                  <div className='detail-field'>
                    <div className='detail-field__label'>Count</div>
                    <div className='detail-field__value'>{bestResponse.best_group.count}</div>
                  </div>
                </div>
                <pre className='detail-field__value' style={{ whiteSpace: 'pre-wrap', marginTop: '0.75rem' }}>
                  {JSON.stringify(bestResponse.best_group.hyperparams, null, 2)}
                </pre>
              </section>
            ) : (
              <EmptyState title='No best configuration' description='No groups matched the selected filters.' />
            )}
          </div>
        </div>
      )}

      <section className='detail-section'>
        <h2 className='detail-section__title'>Best Configuration Settings</h2>
        <div className='leaderboard-filters'>
          <div className='leaderboard-filters__field'>
            <label className='leaderboard-filters__label'>Direction</label>
            <select
              className='leaderboard-filters__select'
              value={bestDirection}
              onChange={(e) => setBestDirection(e.target.value as Direction)}
            >
              <option value='max'>higher is better</option>
              <option value='min'>lower is better</option>
            </select>
          </div>
          <div className='leaderboard-filters__field'>
            <label className='leaderboard-filters__label'>Group by hyperparams</label>
            <input
              className='leaderboard-filters__input'
              value={bestGroupByInput}
              onChange={(e) => setBestGroupByInput(e.target.value)}
              placeholder='embedding_dim,learning_rate,batch_size'
            />
          </div>
        </div>
      </section>
    </div>
  )
}
