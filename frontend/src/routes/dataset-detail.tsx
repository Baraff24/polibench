import { useLoaderData, useNavigate } from 'react-router'
import { Badge, EmptyState, PageHeader, StatCard } from '../components'
import { datasetService } from '../services'
import type { DatasetPublic, DatasetVersionSummary } from '../models'
import type { Params } from 'react-router'

export async function loader({ params }: { params: Params }) {
  const datasetUuid = params.uuid as string
  const [dataset, versions] = await Promise.all([
    datasetService.getByUuid(datasetUuid),
    datasetService.getVersions(datasetUuid),
  ])
  return { dataset, versions }
}

export default function DatasetDetail() {
  const navigate = useNavigate()
  const { dataset, versions } = useLoaderData() as {
    dataset: DatasetPublic
    versions: DatasetVersionSummary[]
  }

  let visibilityVariant: 'success' | 'warning' = 'warning'
  if (dataset.visibility === 'public') {
    visibilityVariant = 'success'
  }

  return (
    <div className='page container'>
      <PageHeader title={dataset.name}>
        <Badge text={dataset.visibility} variant={visibilityVariant} />
      </PageHeader>

      <div className='stat-grid'>
        <StatCard label='Versions' value={String(dataset.versions_count)} />
      </div>

      <section className='detail-section'>
        <h2 className='detail-section__title'>Information</h2>
        <div className='detail-grid'>
          <div className='detail-field'>
            <div className='detail-field__label'>Task</div>
            <div className='detail-field__value'>{dataset.task.replace('_', ' ')}</div>
          </div>
          <div className='detail-field'>
            <div className='detail-field__label'>Created</div>
            <div className='detail-field__value'>
              {new Date(dataset.created_at).toLocaleDateString()}
            </div>
          </div>
          <div className='detail-field'>
            <div className='detail-field__label'>Latest Version</div>
            <div className='detail-field__value'>{dataset.latest_version || '—'}</div>
          </div>
        </div>
      </section>

      {dataset.description && (
        <section className='detail-section'>
          <h2 className='detail-section__title'>Description</h2>
          <p className='detail-field__value'>{dataset.description}</p>
        </section>
      )}

      <section className='detail-section'>
        <h2 className='detail-section__title'>Versions</h2>
        {versions.length === 0 ? (
          <EmptyState
            title='No versions yet'
            description='Create a DatasetVersion to start running experiments.'
          />
        ) : (
          <div className='card-grid'>
            {versions.map((version) => (
              <div
                key={version.uuid}
                className='dataset-card'
                onClick={() => navigate(`/dataset-versions/${version.uuid}`)}
              >
                <div className='dataset-card__header'>
                  <span className='dataset-card__name'>v{version.version}</span>
                  <Badge text={version.status} variant='info' />
                </div>
                <div className='dataset-card__meta'>
                  <span>{version.n_users ?? '—'} users</span>
                  <span>{version.n_items ?? '—'} items</span>
                  <span>{version.density ?? '—'} density</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
