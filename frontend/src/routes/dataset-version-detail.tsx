import { useLoaderData, useNavigate } from 'react-router'
import { useState } from 'react'
import { Badge, DataTable, PageHeader, StatCard } from '../components'
import type { Column } from '../components'
import { datasetService } from '../services'
import type {
  DatasetVersionPublic,
  DatasetVersionYamlPublic,
  PipelineSummary,
  ResourcePublic,
  SourceWithResourcesPublic,
} from '../models'
import type { Params } from 'react-router'

type YamlKind = 'dataset' | 'version' | 'characteristics'

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

  const [version, sourcesWithResources, pipelines, datasetYaml, versionYaml, characteristicsYaml] =
    await Promise.all([
      datasetService.getVersionByUuid(versionUuid),
      datasetService.getVersionSourcesWithResources(versionUuid),
      datasetService.getVersionPipelines(versionUuid),
      safeGetYaml('dataset'),
      safeGetYaml('version'),
      safeGetYaml('characteristics'),
    ])

  return {
    version,
    sourcesWithResources,
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

  const { version, sourcesWithResources, pipelines, yamls } = useLoaderData() as {
    version: DatasetVersionPublic
    sourcesWithResources: SourceWithResourcesPublic[]
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

  const hasYamlContent = yamlKinds.some(({ kind }) => Boolean(yamls[kind].content?.trim()))

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

      {pipelines.length > 0 && (
        <section className='detail-section'>
          <h2 className='detail-section__title'>Pipelines</h2>
          <DataTable
            columns={pipelineColumns}
            rows={pipelines}
            rowKey={(row) => row.uuid}
            onRowClick={(row) => navigate(`/pipelines/${row.uuid}`)}
          />
        </section>
      )}

      {hasYamlContent && (
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
      )}

      {sourcesWithResources.length > 0 && (
        <section className='detail-section'>
          <h2 className='detail-section__title'>Sources & Resources</h2>
          <div className='detail-grid' style={{ gridTemplateColumns: '1fr' }}>
            {sourcesWithResources.map((source) => (
              <details key={source.uuid} className='pipeline-chain__details' open>
                <summary>
                  {source.name} ({source.source_type}) - {source.resources.length} resources
                </summary>
                <div className='detail-grid' style={{ marginTop: '0.75rem' }}>
                  <div className='detail-field'>
                    <div className='detail-field__label'>Downloadable</div>
                    <div className='detail-field__value'>{source.downloadable ? 'yes' : 'no'}</div>
                  </div>
                  <div className='detail-field'>
                    <div className='detail-field__label'>URL</div>
                    <div className='detail-field__value'>{source.url || '—'}</div>
                  </div>
                  <div className='detail-field'>
                    <div className='detail-field__label'>Filename</div>
                    <div className='detail-field__value'>{source.filename || '—'}</div>
                  </div>
                </div>
                {source.resources.length > 0 && (
                  <div style={{ marginTop: '0.75rem' }}>
                    <DataTable
                      columns={resourceColumns}
                      rows={source.resources}
                      rowKey={(row) => row.uuid}
                    />
                  </div>
                )}
              </details>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
