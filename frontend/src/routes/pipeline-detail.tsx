import { useLoaderData, useNavigate } from 'react-router'
import { Badge, DataTable, EmptyState, PageHeader } from '../components'
import type { Column } from '../components'
import { datasetService } from '../services'
import type { ExperimentSummary, PipelinePublic, PipelineYamlPublic } from '../models'
import type { Params } from 'react-router'

type PipelinePhase = 'ingest' | 'transform' | 'split' | 'features' | 'other'

const pipelinePhaseLabel: Record<PipelinePhase, string> = {
  ingest: 'Ingest',
  transform: 'Transform',
  split: 'Split',
  features: 'Features',
  other: 'Generic',
}

const resolvePipelinePhase = (operation: string): PipelinePhase => {
  const normalized = operation.trim().toLowerCase()
  if (
    normalized.includes('load') ||
    normalized.includes('read') ||
    normalized.includes('parse') ||
    normalized.includes('ingest')
  ) {
    return 'ingest'
  }
  if (
    normalized.includes('split') ||
    normalized.includes('leave_one_out') ||
    normalized.includes('temporal')
  ) {
    return 'split'
  }
  if (
    normalized.includes('feature') ||
    normalized.includes('encode') ||
    normalized.includes('token')
  ) {
    return 'features'
  }
  if (
    normalized.includes('normalize') ||
    normalized.includes('clean') ||
    normalized.includes('filter') ||
    normalized.includes('dedup') ||
    normalized.includes('map')
  ) {
    return 'transform'
  }
  return 'other'
}

const stringifyParamValue = (value: unknown): string => {
  if (value === null || value === undefined) {
    return '—'
  }
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

const experimentColumns: Column<ExperimentSummary>[] = [
  { key: 'run_name', header: 'Run', render: (row) => row.run_name || '—' },
  { key: 'model', header: 'Model', render: (row) => row.model_name || row.model_uuid },
  { key: 'status', header: 'Status', render: (row) => row.status },
  {
    key: 'created_at',
    header: 'Created',
    render: (row) => new Date(row.created_at).toLocaleString(),
  },
]

export async function loader({ params }: { params: Params }) {
  const pipelineUuid = params.uuid as string
  const [pipeline, experiments, yaml] = await Promise.all([
    datasetService.getPipelineByUuid(pipelineUuid),
    datasetService.getPipelineExperiments(pipelineUuid),
    datasetService.getPipelineYaml(pipelineUuid).catch(
      () =>
        ({
          pipeline_uuid: pipelineUuid,
          content: '',
        }) as PipelineYamlPublic,
    ),
  ])

  return { pipeline, experiments, yaml }
}

export default function PipelineDetail() {
  const navigate = useNavigate()
  const { pipeline, experiments, yaml } = useLoaderData() as {
    pipeline: PipelinePublic
    experiments: ExperimentSummary[]
    yaml: PipelineYamlPublic
  }

  const uniqueOperationsCount = new Set(
    pipeline.blocks.map((block) => block.operation || 'operation'),
  ).size

  const downloadYaml = () => {
    const blob = new Blob([yaml.content || ''], { type: 'text/yaml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${pipeline.code}.yml`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <div className='page container'>
      <PageHeader title={`Pipeline ${pipeline.code}`}>
        <Badge text={pipeline.status} variant='info' />
      </PageHeader>

      <section className='detail-section'>
        <h2 className='detail-section__title'>Pipeline Chain</h2>
        {pipeline.blocks.length === 0 ? (
          <EmptyState title='No pipeline steps' description='No pipeline YAML parsed yet.' />
        ) : (
          <>
            <div className='pipeline-chain__summary'>
              <span className='pipeline-chain__summary-item'>{pipeline.blocks.length} steps</span>
              <span className='pipeline-chain__summary-item'>{uniqueOperationsCount} operations</span>
            </div>
            <div className='pipeline-chain'>
              {pipeline.blocks.map((block, index) => {
                const phase = resolvePipelinePhase(block.operation || 'operation')
                const paramsCount = Object.keys(block.params).length
                return (
                  <div key={`${block.name}-${index}`} className='pipeline-chain__item'>
                    <div className='pipeline-chain__block'>
                      <div className='pipeline-chain__header'>
                        <span className='pipeline-chain__index'>{index + 1}</span>
                        <div>
                          <div className='pipeline-chain__title'>{block.name}</div>
                          <div className='pipeline-chain__op'>{block.operation || 'operation'}</div>
                        </div>
                      </div>
                      <div className='pipeline-chain__meta'>
                        <span className={`pipeline-chain__badge pipeline-chain__badge--${phase}`}>
                          {pipelinePhaseLabel[phase]}
                        </span>
                        <span className='pipeline-chain__badge pipeline-chain__badge--neutral'>
                          {paramsCount} params
                        </span>
                      </div>
                      <details className='pipeline-chain__details'>
                        <summary>{paramsCount > 0 ? 'View parameters' : 'No parameters'}</summary>
                        {paramsCount > 0 && (
                          <div className='pipeline-chain__params'>
                            {Object.entries(block.params).map(([key, value]) => (
                              <div key={key} className='pipeline-chain__param'>
                                <span className='pipeline-chain__param-key'>{key}</span>
                                <span className='pipeline-chain__param-value'>
                                  {stringifyParamValue(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </details>
                    </div>
                    {index < pipeline.blocks.length - 1 && (
                      <div className='pipeline-chain__arrow'>→</div>
                    )}
                  </div>
                )
              })}
            </div>
          </>
        )}
      </section>

      <section className='detail-section'>
        <h2 className='detail-section__title'>Pipeline YAML</h2>
        <div className='form__actions'>
          <button type='button' className='btn btn--outline' onClick={downloadYaml}>
            Download
          </button>
        </div>
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
          {yaml.content || '# empty'}
        </pre>
      </section>

      <section className='detail-section'>
        <h2 className='detail-section__title'>Experiments</h2>
        {experiments.length === 0 ? (
          <EmptyState
            title='No experiments yet'
            description='No experiment has been submitted for this pipeline.'
          />
        ) : (
          <DataTable
            columns={experimentColumns}
            rows={experiments}
            rowKey={(row) => row.uuid}
            onRowClick={(row) => navigate(`/experiments/${row.uuid}`)}
          />
        )}
      </section>
    </div>
  )
}
