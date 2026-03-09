import { useLoaderData } from 'react-router'
import { PageHeader, Badge, StatCard } from '../components'
import { datasetService } from '../services'
import type { DatasetPublic } from '../models'
import type { Params } from 'react-router'

export async function loader({ params }: { params: Params }) {
  const dataset = await datasetService.getByUuid(params.uuid as string)
  return { dataset }
}

export default function DatasetDetail() {
  const { dataset } = useLoaderData() as { dataset: DatasetPublic }

  return (
    <div className='page container'>
      <PageHeader title={dataset.name}>
        <Badge
          text={dataset.visibility}
          variant={dataset.visibility === 'public' ? 'success' : 'warning'}
        />
      </PageHeader>

      {/* Stats */}
      {dataset.splits && (
        <div className='stat-grid'>
          {dataset.splits.train !== null && (
            <StatCard label='Train' value={dataset.splits.train.toLocaleString()} />
          )}
          {dataset.splits.test !== null && (
            <StatCard label='Test' value={dataset.splits.test.toLocaleString()} />
          )}
          {dataset.splits.validation !== null && (
            <StatCard label='Validation' value={dataset.splits.validation.toLocaleString()} />
          )}
        </div>
      )}

      {/* Details */}
      <section className='detail-section'>
        <h2 className='detail-section__title'>Information</h2>
        <div className='detail-grid'>
          <div className='detail-field'>
            <div className='detail-field__label'>Version</div>
            <div className='detail-field__value'>{dataset.version}</div>
          </div>
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
        </div>
      </section>

      {dataset.description && (
        <section className='detail-section'>
          <h2 className='detail-section__title'>Description</h2>
          <p className='detail-field__value'>{dataset.description}</p>
        </section>
      )}
    </div>
  )
}
