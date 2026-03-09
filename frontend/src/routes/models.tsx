import { useLoaderData, useNavigate } from 'react-router'
import { PageHeader, EmptyState, DataTable } from '../components'
import type { Column } from '../components'
import { mlModelService } from '../services'
import { useAuth } from '../contexts/auth'
import type { MLModelSummary } from '../models'

export async function loader() {
  const models = await mlModelService.getAll()
  return { models }
}

const columns: Column<MLModelSummary>[] = [
  { key: 'name', header: 'Name', render: (m) => m.name },
  { key: 'family', header: 'Family', render: (m) => m.family || '—' },
  {
    key: 'paper',
    header: 'Paper',
    render: (m) => {
      if (!m.paper_url) return '—'
      return (
        <a href={m.paper_url} target='_blank' rel='noreferrer' onClick={(e) => e.stopPropagation()}>
          Link
        </a>
      )
    },
  },
]

export default function Models() {
  const { models } = useLoaderData() as { models: MLModelSummary[] }
  const navigate = useNavigate()
  const { user } = useAuth()

  const headerAction = user ? (
    <button className='btn btn--primary btn--sm' onClick={() => navigate('/models/new')}>
      + New Model
    </button>
  ) : undefined

  if (models.length === 0) {
    return (
      <div className='page container'>
        <PageHeader title='Models' action={headerAction} />
        <EmptyState title='No models yet' description='Register an algorithm to get started.' />
      </div>
    )
  }

  return (
    <div className='page container'>
      <PageHeader title='Models' action={headerAction} />
      <DataTable
        columns={columns}
        rows={models}
        rowKey={(m) => m.uuid}
        onRowClick={(m) => navigate(`/models/${m.uuid}`)}
      />
    </div>
  )
}
