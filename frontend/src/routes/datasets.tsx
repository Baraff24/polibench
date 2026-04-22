import { useLoaderData, useNavigate } from 'react-router'
import { PageHeader, EmptyState, Badge } from '../components'
import { datasetService } from '../services'
import { useAuth } from '../contexts/auth'
import type { DatasetSummary } from '../models'

export async function loader() {
  const datasets = await datasetService.getAll()
  return { datasets }
}

export default function Datasets() {
  const { datasets } = useLoaderData() as { datasets: DatasetSummary[] }
  const navigate = useNavigate()
  const { user } = useAuth()

  const headerAction = user ? (
    <button className='btn btn--primary btn--sm' onClick={() => navigate('/datasets/new')}>
      + New Dataset
    </button>
  ) : undefined

  if (datasets.length === 0) {
    return (
      <div className='page container'>
        <PageHeader title='Datasets' action={headerAction} />
        <EmptyState title='No datasets yet' description='Create one to get started.' />
      </div>
    )
  }

  return (
    <div className='page container'>
      <PageHeader title='Datasets' action={headerAction} />
      <div className='card-grid'>
        {datasets.map((ds) => {
          let badgeVariant: 'success' | 'warning' = 'warning'
          if (ds.visibility === 'public') {
            badgeVariant = 'success'
          }
          return (
            <div
              key={ds.uuid}
              className='dataset-card'
              onClick={() => navigate(`/datasets/${ds.uuid}`)}
            >
              <div className='dataset-card__header'>
                <span className='dataset-card__name'>{ds.name}</span>
                <Badge text={ds.visibility} variant={badgeVariant} />
              </div>
              <div className='dataset-card__meta'>
                <span>{ds.latest_version ? `latest v${ds.latest_version}` : 'no versions'}</span>
                <span>{ds.versions_count} version{ds.versions_count === 1 ? '' : 's'}</span>
                <span>{ds.task.replace('_', ' ')}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
