import { useLoaderData } from 'react-router'
import { PageHeader } from '../components'
import { mlModelService } from '../services'
import type { MLModelPublic } from '../models'
import type { Params } from 'react-router'

export async function loader({ params }: { params: Params }) {
  const model = await mlModelService.getByUuid(params.uuid as string)
  return { model }
}

export default function ModelDetail() {
  const { model } = useLoaderData() as { model: MLModelPublic }

  return (
    <div className='page container'>
      <PageHeader title={model.name} />

      <section className='detail-section'>
        <h2 className='detail-section__title'>Information</h2>
        <div className='detail-grid'>
          <div className='detail-field'>
            <div className='detail-field__label'>Family</div>
            <div className='detail-field__value'>{model.family || '—'}</div>
          </div>
          <div className='detail-field'>
            <div className='detail-field__label'>Implementation</div>
            <div className='detail-field__value'>{model.implementation || '—'}</div>
          </div>
          <div className='detail-field'>
            <div className='detail-field__label'>Paper</div>
            <div className='detail-field__value'>
              {model.paper_url && (
                <a href={model.paper_url} target='_blank' rel='noreferrer'>
                  {model.paper_url}
                </a>
              )}
              {!model.paper_url && '—'}
            </div>
          </div>
          <div className='detail-field'>
            <div className='detail-field__label'>Created</div>
            <div className='detail-field__value'>
              {new Date(model.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>
      </section>

      {model.hyperparams && Object.keys(model.hyperparams).length > 0 && (
        <section className='detail-section'>
          <h2 className='detail-section__title'>Hyperparameters</h2>
          <div className='detail-grid'>
            {Object.entries(model.hyperparams).map(([key, val]) => (
              <div key={key} className='detail-field'>
                <div className='detail-field__label'>{key}</div>
                <div className='detail-field__value'>{String(val)}</div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
