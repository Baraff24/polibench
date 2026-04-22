import { useState } from 'react'
import { useLoaderData, useNavigate } from 'react-router'
import { Badge, EmptyState, PageHeader, StatCard } from '../components'
import { datasetService } from '../services'
import { useAuth } from '../contexts/auth'
import { useSnackBar } from '../contexts/snackbar'
import type { DatasetPublic, DatasetVersionSummary, VersionStatus } from '../models'
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
  const { user } = useAuth()
  const { showSnackBar } = useSnackBar()
  const { dataset, versions } = useLoaderData() as {
    dataset: DatasetPublic
    versions: DatasetVersionSummary[]
  }
  const [creatingVersion, setCreatingVersion] = useState(false)
  const [versionName, setVersionName] = useState('')
  const [versionStatus, setVersionStatus] = useState<VersionStatus>('draft')
  const [releaseNotes, setReleaseNotes] = useState('')
  const [datasetYamlRaw, setDatasetYamlRaw] = useState('')
  const [pipelineYamlRaw, setPipelineYamlRaw] = useState('')
  const [characteristicsYamlRaw, setCharacteristicsYamlRaw] = useState('')

  let visibilityVariant: 'success' | 'warning' = 'warning'
  if (dataset.visibility === 'public') {
    visibilityVariant = 'success'
  }

  const readYamlFile = async (
    file: File | null,
    setter: (value: string) => void,
  ): Promise<void> => {
    if (!file) {
      return
    }
    const text = await file.text()
    setter(text)
  }

  const submitVersion = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!user) {
      showSnackBar('Please login first.', 'error')
      return
    }
    if (!versionName.trim()) {
      showSnackBar('Version is required.', 'error')
      return
    }
    setCreatingVersion(true)
    try {
      await datasetService.createVersion(dataset.uuid, {
        version: versionName.trim(),
        status: versionStatus,
        release_notes: releaseNotes.trim() || undefined,
        dataset_yaml_raw: datasetYamlRaw.trim() || undefined,
        pipeline_yaml_raw: pipelineYamlRaw.trim() || undefined,
        characteristics_yaml_raw: characteristicsYamlRaw.trim() || undefined,
      })
      showSnackBar('Dataset version created.', 'success')
      navigate(0)
    } catch {
      showSnackBar('Error creating dataset version.', 'error')
    } finally {
      setCreatingVersion(false)
    }
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

      <section className='detail-section'>
        <h2 className='detail-section__title'>New Version (YAML Submit)</h2>
        {!user ? (
          <EmptyState
            title='Login required'
            description='Sign in to create a new DatasetVersion and submit YAML files.'
          />
        ) : (
          <form className='form' onSubmit={submitVersion}>
            <div className='field'>
              <label className='field__label' htmlFor='version-name'>
                Version
              </label>
              <input
                id='version-name'
                className='field__input'
                value={versionName}
                onChange={(e) => setVersionName(e.target.value)}
                placeholder='e.g. v2.0'
                required
              />
            </div>

            <div className='field'>
              <label className='field__label' htmlFor='version-status'>
                Status
              </label>
              <select
                id='version-status'
                className='field__input'
                value={versionStatus}
                onChange={(e) => setVersionStatus(e.target.value as VersionStatus)}
              >
                <option value='draft'>draft</option>
                <option value='ready'>ready</option>
                <option value='processing'>processing</option>
                <option value='failed'>failed</option>
              </select>
            </div>

            <div className='field'>
              <label className='field__label' htmlFor='version-notes'>
                Release Notes
              </label>
              <textarea
                id='version-notes'
                className='field__input'
                rows={2}
                value={releaseNotes}
                onChange={(e) => setReleaseNotes(e.target.value)}
              />
            </div>

            <div className='field'>
              <label className='field__label' htmlFor='dataset-yaml-file'>
                Dataset YAML file
              </label>
              <input
                id='dataset-yaml-file'
                type='file'
                accept='.yml,.yaml,text/yaml,text/plain'
                className='field__input'
                onChange={(e) => readYamlFile(e.target.files?.[0] ?? null, setDatasetYamlRaw)}
              />
            </div>
            <div className='field'>
              <label className='field__label' htmlFor='dataset-yaml'>
                Dataset YAML
              </label>
              <textarea
                id='dataset-yaml'
                className='field__input'
                rows={8}
                value={datasetYamlRaw}
                onChange={(e) => setDatasetYamlRaw(e.target.value)}
                placeholder='Paste dataset YAML here...'
              />
            </div>

            <div className='field'>
              <label className='field__label' htmlFor='pipeline-yaml-file'>
                Pipeline YAML file
              </label>
              <input
                id='pipeline-yaml-file'
                type='file'
                accept='.yml,.yaml,text/yaml,text/plain'
                className='field__input'
                onChange={(e) => readYamlFile(e.target.files?.[0] ?? null, setPipelineYamlRaw)}
              />
            </div>
            <div className='field'>
              <label className='field__label' htmlFor='pipeline-yaml'>
                Pipeline YAML
              </label>
              <textarea
                id='pipeline-yaml'
                className='field__input'
                rows={8}
                value={pipelineYamlRaw}
                onChange={(e) => setPipelineYamlRaw(e.target.value)}
                placeholder='Paste pipeline YAML here...'
              />
            </div>

            <div className='field'>
              <label className='field__label' htmlFor='characteristics-yaml-file'>
                Characteristics YAML file
              </label>
              <input
                id='characteristics-yaml-file'
                type='file'
                accept='.yml,.yaml,text/yaml,text/plain'
                className='field__input'
                onChange={(e) =>
                  readYamlFile(e.target.files?.[0] ?? null, setCharacteristicsYamlRaw)
                }
              />
            </div>
            <div className='field'>
              <label className='field__label' htmlFor='characteristics-yaml'>
                Characteristics YAML
              </label>
              <textarea
                id='characteristics-yaml'
                className='field__input'
                rows={8}
                value={characteristicsYamlRaw}
                onChange={(e) => setCharacteristicsYamlRaw(e.target.value)}
                placeholder='Paste characteristics YAML here...'
              />
            </div>

            <div className='form__actions'>
              <button type='submit' className='btn btn--primary' disabled={creatingVersion}>
                {creatingVersion ? 'Creating...' : 'Create Dataset Version'}
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  )
}
