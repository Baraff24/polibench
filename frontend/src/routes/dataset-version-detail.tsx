import { useLoaderData, useNavigate } from 'react-router'
import { useState } from 'react'
import { Badge, DataTable, EmptyState, PageHeader, StatCard } from '../components'
import type { Column } from '../components'
import { datasetService } from '../services'
import type {
  DatasetVersionPublic,
  DatasetVersionYamlPublic,
  PipelineSummary,
  ResourcePublic,
  SourcePublic,
} from '../models'
import type { Params } from 'react-router'

type YamlKind = 'dataset' | 'version' | 'characteristics'

const sourceColumns: Column<SourcePublic>[] = [
  { key: 'name', header: 'Name', render: (row) => row.name },
  { key: 'source_type', header: 'Type', render: (row) => row.source_type },
  {
    key: 'downloadable',
    header: 'Downloadable',
    render: (row) => (row.downloadable ? 'yes' : 'no'),
  },
  { key: 'url', header: 'URL', render: (row) => row.url || '—' },
]

const resourceColumns: Column<ResourcePublic>[] = [
  { key: 'name', header: 'Name', render: (row) => row.name },
  { key: 'type', header: 'Type', render: (row) => row.type },
  { key: 'format', header: 'Format', render: (row) => row.format || '—' },
  { key: 'required', header: 'Required', render: (row) => (row.required ? 'yes' : 'no') },
]

const pipelineColumns: Column<PipelineSummary>[] = [
  { key: 'code', header: 'Code', render: (row) => row.code },
  { key: 'status', header: 'Status', render: (row) => row.status },
  { key: 'steps', header: 'Steps', render: (row) => row.steps_count },
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

  const [version, sources, resources, pipelines, datasetYaml, versionYaml, characteristicsYaml] =
    await Promise.all([
      datasetService.getVersionByUuid(versionUuid),
      datasetService.getVersionSources(versionUuid),
      datasetService.getVersionResources(versionUuid),
      datasetService.getVersionPipelines(versionUuid),
      safeGetYaml('dataset'),
      safeGetYaml('version'),
      safeGetYaml('characteristics'),
    ])

  return {
    version,
    sources,
    resources,
    pipelines,
    yamls: {
      dataset: datasetYaml,
      version: versionYaml,
      characteristics: characteristicsYaml,
    },
  }
}

export default function DatasetVersionDetail() {
  const navigate = useNavigate()
  const [visibleYaml, setVisibleYaml] = useState<YamlKind | null>(null)

  const { version, sources, resources, pipelines, yamls } = useLoaderData() as {
    version: DatasetVersionPublic
    sources: SourcePublic[]
    resources: ResourcePublic[]
    pipelines: PipelineSummary[]
    yamls: Record<YamlKind, DatasetVersionYamlPublic>
  }

  const yamlKinds: { kind: YamlKind; label: string }[] = [
    { kind: 'dataset', label: 'Dataset YAML' },
    { kind: 'version', label: 'Version YAML' },
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
        <h2 className='detail-section__title'>Pipelines</h2>
        {pipelines.length === 0 ? (
          <EmptyState
            title='No pipelines yet'
            description='Create a pipeline for this dataset version to run experiments.'
          />
        ) : (
          <DataTable
            columns={pipelineColumns}
            rows={pipelines}
            rowKey={(row) => row.uuid}
            onRowClick={(row) => navigate(`/pipelines/${row.uuid}`)}
          />
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
              border: '1px solid #d0d7de',
              borderRadius: '8px',
              background: '#ffffff',
              color: '#111111',
              fontWeight: 500,
              lineHeight: 1.45,
            }}
          >
            {yamls[visibleYaml].content || '# empty'}
          </pre>
        )}
      </section>

      <section className='detail-section'>
        <h2 className='detail-section__title'>Sources</h2>
        {sources.length === 0 ? (
          <EmptyState title='No sources' description='No sources found in version YAML.' />
        ) : (
          <DataTable columns={sourceColumns} rows={sources} rowKey={(row) => row.uuid} />
        )}
      </section>

      <section className='detail-section'>
        <h2 className='detail-section__title'>Resources</h2>
        {resources.length === 0 ? (
          <EmptyState title='No resources' description='No resources found in version YAML.' />
        ) : (
          <DataTable columns={resourceColumns} rows={resources} rowKey={(row) => row.uuid} />
        )}
      </section>
    </div>
  )
}
