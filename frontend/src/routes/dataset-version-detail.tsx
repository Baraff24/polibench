import { useLoaderData, useNavigate } from 'react-router'
import { useState } from 'react'
import { Badge, DataTable, EmptyState, PageHeader, StatCard } from '../components'
import type { Column } from '../components'
import { datasetService, experimentService } from '../services'
import type {
  DatasetVersionPipelinePublic,
  DatasetVersionPublic,
  DatasetVersionYamlPublic,
  ExperimentSummary,
  ResourcePublic,
  SourcePublic,
} from '../models'
import type { Params } from 'react-router'

type YamlKind = 'dataset' | 'version' | 'pipeline' | 'characteristics'
type PipelineRow = DatasetVersionPipelinePublic['blocks'][number]

const pipelineColumns: Column<PipelineRow>[] = [
  { key: 'name', header: 'Step', render: (row) => row.name },
  { key: 'operation', header: 'Operation', render: (row) => row.operation },
  {
    key: 'params',
    header: 'Params',
    render: (row) =>
      Object.keys(row.params).length > 0 ? JSON.stringify(row.params) : '—',
  },
]

const sourceColumns: Column<SourcePublic>[] = [
  { key: 'name', header: 'Name', render: (row) => row.name },
  { key: 'source_type', header: 'Type', render: (row) => row.source_type },
  { key: 'downloadable', header: 'Downloadable', render: (row) => (row.downloadable ? 'yes' : 'no') },
  { key: 'url', header: 'URL', render: (row) => row.url || '—' },
]

const resourceColumns: Column<ResourcePublic>[] = [
  { key: 'name', header: 'Name', render: (row) => row.name },
  { key: 'type', header: 'Type', render: (row) => row.type },
  { key: 'format', header: 'Format', render: (row) => row.format || '—' },
  { key: 'required', header: 'Required', render: (row) => (row.required ? 'yes' : 'no') },
]

const experimentColumns: Column<ExperimentSummary>[] = [
  { key: 'run_name', header: 'Run', render: (row) => row.run_name || '—' },
  { key: 'model', header: 'Model', render: (row) => row.model_name || row.model_uuid },
  { key: 'status', header: 'Status', render: (row) => row.status },
  {
    key: 'created_at',
    header: 'Created',
    render: (row) => new Date(row.created_at).toLocaleString(),
  },
]

export async function loader({ params }: { params: Params }) {
  const versionUuid = params.uuid as string

  const safeGetYaml = async (kind: YamlKind): Promise<DatasetVersionYamlPublic> => {
    try {
      return await datasetService.getVersionYaml(versionUuid, kind)
    } catch {
      return {
        dataset_version_uuid: versionUuid,
        kind,
        content: '',
      }
    }
  }

  const [
    version,
    sources,
    resources,
    pipeline,
    datasetYaml,
    versionYaml,
    pipelineYaml,
    characteristicsYaml,
    experiments,
  ] = await Promise.all([
    datasetService.getVersionByUuid(versionUuid),
    datasetService.getVersionSources(versionUuid),
    datasetService.getVersionResources(versionUuid),
    datasetService.getVersionPipeline(versionUuid),
    safeGetYaml('dataset'),
    safeGetYaml('version'),
    safeGetYaml('pipeline'),
    safeGetYaml('characteristics'),
    experimentService.listByDatasetVersion(versionUuid),
  ])
  return {
    version,
    sources,
    resources,
    pipeline,
    experiments,
    yamls: {
      dataset: datasetYaml,
      version: versionYaml,
      pipeline: pipelineYaml,
      characteristics: characteristicsYaml,
    },
  }
}

export default function DatasetVersionDetail() {
  const navigate = useNavigate()
  const [visibleYaml, setVisibleYaml] = useState<YamlKind | null>(null)

  const { version, sources, resources, pipeline, experiments, yamls } =
    useLoaderData() as {
    version: DatasetVersionPublic
    sources: SourcePublic[]
    resources: ResourcePublic[]
    pipeline: DatasetVersionPipelinePublic
    experiments: ExperimentSummary[]
    yamls: Record<YamlKind, DatasetVersionYamlPublic>
  }

  const yamlKinds: { kind: YamlKind; label: string }[] = [
    { kind: 'dataset', label: 'Dataset YAML' },
    { kind: 'version', label: 'Version YAML' },
    { kind: 'pipeline', label: 'Pipeline YAML' },
    { kind: 'characteristics', label: 'Characteristics YAML' },
  ]

  const toggleYaml = (kind: YamlKind) => {
    if (visibleYaml === kind) {
      setVisibleYaml(null)
      return
    }
    setVisibleYaml(kind)
  }

  const downloadYaml = (kind: YamlKind) => {
    const payload = yamls[kind]
    const blob = new Blob([payload.content || ''], { type: 'text/yaml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${version.version}_${kind}.yml`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <div className='page container'>
      <PageHeader title={`Dataset Version v${version.version}`}>
        <Badge text={version.status} variant='info' />
      </PageHeader>

      <div className='stat-grid'>
        <StatCard label='Users' value={version.n_users?.toLocaleString() || '—'} />
        <StatCard label='Items' value={version.n_items?.toLocaleString() || '—'} />
        <StatCard
          label='Interactions'
          value={version.n_interactions?.toLocaleString() || '—'}
        />
        <StatCard label='Density' value={version.density?.toFixed(6) || '—'} />
      </div>

      <section className='detail-section'>
        <h2 className='detail-section__title'>Pipeline</h2>
        {pipeline.blocks.length === 0 ? (
          <EmptyState title='No pipeline steps' description='No pipeline YAML parsed yet.' />
        ) : (
          <>
            <div className='pipeline-chain'>
              {pipeline.blocks.map((block, index) => (
                <div key={`${block.name}-${index}`} className='pipeline-chain__item'>
                  <div className='pipeline-chain__block'>
                    <div className='pipeline-chain__title'>{block.name}</div>
                    <div className='pipeline-chain__op'>{block.operation || 'operation'}</div>
                  </div>
                  {index < pipeline.blocks.length - 1 && <div className='pipeline-chain__arrow'>→</div>}
                </div>
              ))}
            </div>
            <DataTable columns={pipelineColumns} rows={pipeline.blocks} rowKey={(row) => row.name} />
          </>
        )}
      </section>

      <section className='detail-section'>
        <h2 className='detail-section__title'>YAML</h2>
        <div className='form__actions'>
          {yamlKinds.map(({ kind, label }) => (
            <div key={kind} style={{ display: 'flex', gap: '0.5rem' }}>
              <button type='button' className='btn btn--outline' onClick={() => toggleYaml(kind)}>
                {visibleYaml === kind ? `Hide ${label}` : `View ${label}`}
              </button>
              <button type='button' className='btn btn--outline' onClick={() => downloadYaml(kind)}>
                Download
              </button>
            </div>
          ))}
        </div>
        {visibleYaml && (
          <pre
            className='detail-field__value'
            style={{
              whiteSpace: 'pre-wrap',
              marginTop: '1rem',
              padding: '1rem',
              border: '1px solid var(--color-border, #ddd)',
              borderRadius: '8px',
              background: '#fafafa',
            }}
          >
            {yamls[visibleYaml].content || '# empty'}
          </pre>
        )}
      </section>

      <section className='detail-section'>
        <h2 className='detail-section__title'>Sources</h2>
        {sources.length === 0 ? (
          <EmptyState title='No sources' description='No sources found in dataset YAML.' />
        ) : (
          <DataTable columns={sourceColumns} rows={sources} rowKey={(row) => row.uuid} />
        )}
      </section>

      <section className='detail-section'>
        <h2 className='detail-section__title'>Resources</h2>
        {resources.length === 0 ? (
          <EmptyState title='No resources' description='No resources found in dataset YAML.' />
        ) : (
          <DataTable columns={resourceColumns} rows={resources} rowKey={(row) => row.uuid} />
        )}
      </section>

      <section className='detail-section'>
        <h2 className='detail-section__title'>Experiments</h2>
        {experiments.length === 0 ? (
          <EmptyState
            title='No experiments yet'
            description='No experiment has been submitted for this dataset version.'
          />
        ) : (
          <DataTable
            columns={experimentColumns}
            rows={experiments}
            rowKey={(row) => row.uuid}
            onRowClick={(row) => navigate(`/experiments/${row.uuid}`)}
          />
        )}
      </section>
    </div>
  )
}
