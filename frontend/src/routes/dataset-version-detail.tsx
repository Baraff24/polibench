import { useLoaderData } from 'react-router'
import { Badge, DataTable, EmptyState, PageHeader, StatCard } from '../components'
import type { Column } from '../components'
import { datasetService } from '../services'
import type {
  DatasetVersionPipelinePublic,
  DatasetVersionPublic,
  ResourcePublic,
  SourcePublic,
} from '../models'
import type { Params } from 'react-router'

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

export async function loader({ params }: { params: Params }) {
  const versionUuid = params.uuid as string
  const [version, sources, resources, pipeline] = await Promise.all([
    datasetService.getVersionByUuid(versionUuid),
    datasetService.getVersionSources(versionUuid),
    datasetService.getVersionResources(versionUuid),
    datasetService.getVersionPipeline(versionUuid),
  ])
  return { version, sources, resources, pipeline }
}

export default function DatasetVersionDetail() {
  const { version, sources, resources, pipeline } = useLoaderData() as {
    version: DatasetVersionPublic
    sources: SourcePublic[]
    resources: ResourcePublic[]
    pipeline: DatasetVersionPipelinePublic
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
          <DataTable columns={pipelineColumns} rows={pipeline.blocks} rowKey={(row) => row.name} />
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
    </div>
  )
}
