import { useLoaderData, useNavigate } from 'react-router'
import { PageHeader, EmptyState, Badge } from '../components'
import { datasetService } from '../services'
import type { DatasetSummary } from '../models'

export async function loader() {
  const datasets = await datasetService.getAll()
  return { datasets }
}

export default function Datasets() {
  const { datasets } = useLoaderData() as { datasets: DatasetSummary[] }
  const navigate = useNavigate()

  if (datasets.length === 0) {
    return (
      <div className='page container'>
        <PageHeader title='Datasets' />
        <EmptyState title='No datasets yet' description='Create one to get started.' />
      </div>
    )
  }

  return (
    <div className='page container'>
      <PageHeader title='Datasets' />
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
                <span>v{ds.version}</span>
                <span>{ds.task.replace('_', ' ')}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
