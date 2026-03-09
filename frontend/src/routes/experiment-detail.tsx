import { useLoaderData, useNavigate } from 'react-router'
import { PageHeader, Badge, DataTable } from '../components'
import type { Column } from '../components'
import { experimentService } from '../services'
import type { ExperimentPublic, ExperimentMetrics, MetricPublic, Split } from '../models'
import type { Params } from 'react-router'

function statusVariant(status: string): 'success' | 'error' | 'warning' | 'info' {
  if (status === 'finished') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'running') return 'info'
  return 'warning'
}

const metricColumns: Column<MetricPublic>[] = [
  { key: 'metric', header: 'Metric', render: (m) => m.metric },
  { key: 'value', header: 'Value', render: (m) => m.value.toFixed(4) },
  { key: 'direction', header: 'Direction', render: (m) => m.direction },
]

export async function loader({ params }: { params: Params }) {
  const uuid = params.uuid as string
  const experiment = await experimentService.getByUuid(uuid)
  let metrics: ExperimentMetrics | null = null
  try {
    metrics = await experimentService.getMetrics(uuid)
  } catch {
    // no metrics yet
  }
  return { experiment, metrics }
}

export default function ExperimentDetail() {
  const { experiment, metrics } = useLoaderData() as {
    experiment: ExperimentPublic
    metrics: ExperimentMetrics | null
  }
  const navigate = useNavigate()

  const splitKeys: Split[] = []
  if (metrics) {
    for (const key of Object.keys(metrics.metrics_by_split)) {
      splitKeys.push(key as Split)
    }
  }

  return (
    <div className='page container'>
      <PageHeader title={experiment.run_name || 'Experiment'}>
        <Badge text={experiment.status} variant={statusVariant(experiment.status)} />
        <button
          className='btn btn--primary btn--sm'
          onClick={() => navigate(`/experiments/${experiment.uuid}/metrics/new`)}
        >
          Submit Metrics
        </button>
      </PageHeader>

      <section className='detail-section'>
        <h2 className='detail-section__title'>Run details</h2>
        <div className='detail-grid'>
          <div className='detail-field'>
            <div className='detail-field__label'>Status</div>
            <div className='detail-field__value'>{experiment.status}</div>
          </div>
          {experiment.seed !== null && (
            <div className='detail-field'>
              <div className='detail-field__label'>Seed</div>
              <div className='detail-field__value'>{experiment.seed}</div>
            </div>
          )}
          <div className='detail-field'>
            <div className='detail-field__label'>Created</div>
            <div className='detail-field__value'>
              {new Date(experiment.created_at).toLocaleDateString()}
            </div>
          </div>
          {experiment.finished_at && (
            <div className='detail-field'>
              <div className='detail-field__label'>Finished</div>
              <div className='detail-field__value'>
                {new Date(experiment.finished_at).toLocaleDateString()}
              </div>
            </div>
          )}
        </div>
      </section>

      {experiment.notes && (
        <section className='detail-section'>
          <h2 className='detail-section__title'>Notes</h2>
          <p className='detail-field__value'>{experiment.notes}</p>
        </section>
      )}

      {experiment.training_config && Object.keys(experiment.training_config).length > 0 && (
        <section className='detail-section'>
          <h2 className='detail-section__title'>Training config</h2>
          <div className='detail-grid'>
            {Object.entries(experiment.training_config).map(([key, val]) => (
              <div key={key} className='detail-field'>
                <div className='detail-field__label'>{key}</div>
                <div className='detail-field__value'>{String(val)}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {splitKeys.map((split) => (
        <section key={split} className='detail-section'>
          <h2 className='detail-section__title'>
            {'Metrics \u2014 '}
            {split}
          </h2>
          <DataTable
            columns={metricColumns}
            rows={metrics!.metrics_by_split[split]}
            rowKey={(m) => m.uuid}
          />
        </section>
      ))}
    </div>
  )
}
