import { useState } from 'react'
import { useLoaderData, useNavigate } from 'react-router'
import { Badge, EmptyState, PageHeader, StatCard } from '../components'
import { datasetService } from '../services'
import { useAuth } from '../contexts/auth'
import { useSnackBar } from '../contexts/snackbar'
import type {
  DatasetPublic,
  DatasetVersionCreate,
  DatasetVersionPreviewPublic,
  DatasetVersionSummary,
  VersionStatus,
} from '../models'
import type { Params } from 'react-router'

type VersionYamlKind = 'dataset' | 'version' | 'pipeline' | 'characteristics'

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
  const [versionYamlRaw, setVersionYamlRaw] = useState('')
  const [pipelineYamlRaw, setPipelineYamlRaw] = useState('')
  const [characteristicsYamlRaw, setCharacteristicsYamlRaw] = useState('')
  const [previewingVersion, setPreviewingVersion] = useState(false)
  const [preview, setPreview] = useState<DatasetVersionPreviewPublic | null>(null)

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

  const buildVersionPayload = (): DatasetVersionCreate => ({
    version: versionName.trim(),
    status: versionStatus,
    release_notes: releaseNotes.trim() || undefined,
    dataset_yaml_raw: datasetYamlRaw.trim() || undefined,
    version_yaml_raw: versionYamlRaw.trim() || undefined,
    pipeline_yaml_raw: pipelineYamlRaw.trim() || undefined,
    characteristics_yaml_raw: characteristicsYamlRaw.trim() || undefined,
  })

  const downloadTextAsFile = (content: string, filename: string) => {
    const blob = new Blob([content || ''], { type: 'text/yaml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  }

  const downloadVersionYaml = async (
    e: React.MouseEvent,
    version: DatasetVersionSummary,
    kind: VersionYamlKind,
  ) => {
    e.stopPropagation()
    try {
      const content = await datasetService.downloadVersionYamlRaw(version.uuid, kind)
      downloadTextAsFile(content, `${dataset.name}_${version.version}_${kind}.yml`)
    } catch {
      showSnackBar(`Cannot download ${kind} YAML for v${version.version}.`, 'error')
    }
  }

  const previewVersion = async () => {
    if (!user) {
      showSnackBar('Please login first.', 'error')
      return
    }
    if (!versionName.trim()) {
      showSnackBar('Version is required before preview.', 'error')
      return
    }
    setPreviewingVersion(true)
    try {
      const parsedPreview = await datasetService.previewVersion(dataset.uuid, buildVersionPayload())
      setPreview(parsedPreview)
      showSnackBar('YAML preview parsed successfully.', 'success')
    } catch {
      setPreview(null)
      showSnackBar('YAML preview failed. Check consistency of dataset/version/source/resource.', 'error')
    } finally {
      setPreviewingVersion(false)
    }
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
      await datasetService.createVersion(dataset.uuid, buildVersionPayload())
      showSnackBar('Dataset version created.', 'success')
      setPreview(null)
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
        <h2 className='detail-section__title'>Dataset Metadata</h2>
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
        <h2 className='detail-section__title'>Version Registry</h2>
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
                <div className='form__actions' style={{ marginTop: '0.5rem' }}>
                  <button
                    type='button'
                    className='btn btn--outline btn--sm'
                    onClick={(e) => {
                      e.stopPropagation()
                      navigate(`/dataset-versions/${version.uuid}`)
                    }}
                  >
                    Open
                  </button>
                  <button
                    type='button'
                    className='btn btn--outline btn--sm'
                    onClick={(e) => downloadVersionYaml(e, version, 'dataset')}
                  >
                    Dataset YAML
                  </button>
                  <button
                    type='button'
                    className='btn btn--outline btn--sm'
                    onClick={(e) => downloadVersionYaml(e, version, 'version')}
                  >
                    Version YAML
                  </button>
                  <button
                    type='button'
                    className='btn btn--outline btn--sm'
                    onClick={(e) => downloadVersionYaml(e, version, 'pipeline')}
                  >
                    Pipeline YAML
                  </button>
                  <button
                    type='button'
                    className='btn btn--outline btn--sm'
                    onClick={(e) => downloadVersionYaml(e, version, 'characteristics')}
                  >
                    Metrics YAML
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className='detail-section'>
        <h2 className='detail-section__title'>New Version (YAML Submit + Preview)</h2>
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
              <label className='field__label' htmlFor='version-yaml-file'>
                Version YAML file
              </label>
              <input
                id='version-yaml-file'
                type='file'
                accept='.yml,.yaml,text/yaml,text/plain'
                className='field__input'
                onChange={(e) => readYamlFile(e.target.files?.[0] ?? null, setVersionYamlRaw)}
              />
            </div>
            <div className='field'>
              <label className='field__label' htmlFor='version-yaml'>
                Version YAML
              </label>
              <textarea
                id='version-yaml'
                className='field__input'
                rows={8}
                value={versionYamlRaw}
                onChange={(e) => setVersionYamlRaw(e.target.value)}
                placeholder='Paste version YAML here...'
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

            {preview && (
              <div className='detail-grid' style={{ marginTop: '0.5rem' }}>
                <div className='detail-field'>
                  <div className='detail-field__label'>Recognized Dataset</div>
                  <div className='detail-field__value'>{preview.recognized_dataset_name || '—'}</div>
                </div>
                <div className='detail-field'>
                  <div className='detail-field__label'>Recognized Version</div>
                  <div className='detail-field__value'>{preview.recognized_version || '—'}</div>
                </div>
                <div className='detail-field'>
                  <div className='detail-field__label'>Parsed Sources</div>
                  <div className='detail-field__value'>{preview.source_count}</div>
                </div>
                <div className='detail-field'>
                  <div className='detail-field__label'>Parsed Resources</div>
                  <div className='detail-field__value'>{preview.resource_count}</div>
                </div>
                <div className='detail-field'>
                  <div className='detail-field__label'>Pipeline Steps</div>
                  <div className='detail-field__value'>{preview.pipeline_steps_count}</div>
                </div>
                <div className='detail-field'>
                  <div className='detail-field__label'>Characteristics</div>
                  <div className='detail-field__value'>
                    users {preview.characteristics.n_users ?? '—'}, items{' '}
                    {preview.characteristics.n_items ?? '—'}, interactions{' '}
                    {preview.characteristics.n_interactions ?? '—'}, density{' '}
                    {preview.characteristics.density ?? '—'}
                  </div>
                </div>
              </div>
            )}

            <div className='form__actions'>
              <button
                type='button'
                className='btn btn--outline'
                disabled={previewingVersion || creatingVersion}
                onClick={previewVersion}
              >
                {previewingVersion ? 'Previewing...' : 'Preview Parse'}
              </button>
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
