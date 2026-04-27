import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { PageHeader } from '../components'
import { datasetService, experimentService, mlModelService } from '../services'
import { useSnackBar } from '../contexts/snackbar'
import type {
  DatasetSummary,
  DatasetVersionSummary,
  MLModelSummary,
  PipelineSummary,
} from '../models'

export default function SubmitExperiment() {
  const navigate = useNavigate()
  const { showSnackBar } = useSnackBar()
  const [loading, setLoading] = useState(false)

  const [datasets, setDatasets] = useState<DatasetSummary[]>([])
  const [versions, setVersions] = useState<DatasetVersionSummary[]>([])
  const [pipelines, setPipelines] = useState<PipelineSummary[]>([])
  const [models, setModels] = useState<MLModelSummary[]>([])

  const [datasetUuid, setDatasetUuid] = useState('')
  const [datasetVersionUuid, setDatasetVersionUuid] = useState('')
  const [pipelineUuid, setPipelineUuid] = useState('')
  const [modelUuid, setModelUuid] = useState('')
  const [runName, setRunName] = useState('')
  const [seed, setSeed] = useState('')
  const [notes, setNotes] = useState('')

  useEffect(() => {
    datasetService.getAll().then(setDatasets)
    mlModelService.getAll().then(setModels)
  }, [])

  useEffect(() => {
    if (!datasetUuid) {
      setVersions([])
      setDatasetVersionUuid('')
      setPipelines([])
      setPipelineUuid('')
      return
    }
    datasetService
      .getVersions(datasetUuid)
      .then((loadedVersions) => {
        setVersions(loadedVersions)
        if (loadedVersions.length > 0) {
          setDatasetVersionUuid(loadedVersions[0].uuid)
        } else {
          setDatasetVersionUuid('')
        }
      })
      .catch(() => {
        setVersions([])
        setDatasetVersionUuid('')
        setPipelines([])
        setPipelineUuid('')
      })
  }, [datasetUuid])

  useEffect(() => {
    if (!datasetVersionUuid) {
      setPipelines([])
      setPipelineUuid('')
      return
    }
    datasetService
      .getVersionPipelines(datasetVersionUuid)
      .then((loadedPipelines) => {
        setPipelines(loadedPipelines)
        if (loadedPipelines.length > 0) {
          setPipelineUuid(loadedPipelines[0].uuid)
        } else {
          setPipelineUuid('')
        }
      })
      .catch(() => {
        setPipelines([])
        setPipelineUuid('')
      })
  }, [datasetVersionUuid])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!datasetVersionUuid || !pipelineUuid || !modelUuid) {
      showSnackBar('Please select dataset version, pipeline and model.', 'error')
      return
    }
    setLoading(true)
    try {
      const experiment = await experimentService.create({
        pipeline_uuid: pipelineUuid,
        model_uuid: modelUuid,
        run_name: runName.trim() || undefined,
        seed: seed ? Number(seed) : undefined,
        notes: notes.trim() || undefined,
      })
      showSnackBar('Experiment submitted!', 'success')
      navigate('/experiments/' + experiment.uuid)
    } catch {
      showSnackBar('Error submitting experiment.', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className='page container container--narrow'>
      <PageHeader title='Submit Experiment' />

      <form className='form' onSubmit={handleSubmit}>
        <div className='field'>
          <label className='field__label' htmlFor='exp-dataset'>
            Dataset
          </label>
          <select
            id='exp-dataset'
            className='field__input'
            value={datasetUuid}
            onChange={(e) => setDatasetUuid(e.target.value)}
            required
          >
            <option value=''>Select a dataset...</option>
            {datasets.map((d) => (
              <option key={d.uuid} value={d.uuid}>
                {d.name} ({d.task})
              </option>
            ))}
          </select>
        </div>

        <div className='field'>
          <label className='field__label' htmlFor='exp-version'>
            Dataset Version
          </label>
          <select
            id='exp-version'
            className='field__input'
            value={datasetVersionUuid}
            onChange={(e) => setDatasetVersionUuid(e.target.value)}
            required
            disabled={!datasetUuid || versions.length === 0}
          >
            <option value=''>
              {datasetUuid ? 'Select a version...' : 'Select dataset first...'}
            </option>
            {versions.map((v) => (
              <option key={v.uuid} value={v.uuid}>
                v{v.version} ({v.status})
              </option>
            ))}
          </select>
        </div>

        <div className='field'>
          <label className='field__label' htmlFor='exp-pipeline'>
            Pipeline
          </label>
          <select
            id='exp-pipeline'
            className='field__input'
            value={pipelineUuid}
            onChange={(e) => setPipelineUuid(e.target.value)}
            required
            disabled={!datasetVersionUuid || pipelines.length === 0}
          >
            <option value=''>
              {datasetVersionUuid ? 'Select a pipeline...' : 'Select version first...'}
            </option>
            {pipelines.map((p) => (
              <option key={p.uuid} value={p.uuid}>
                {p.code} ({p.status}, {p.steps_count} steps)
              </option>
            ))}
          </select>
        </div>

        <div className='field'>
          <label className='field__label' htmlFor='exp-model'>
            Model
          </label>
          <select
            id='exp-model'
            className='field__input'
            value={modelUuid}
            onChange={(e) => setModelUuid(e.target.value)}
            required
          >
            <option value=''>Select a model...</option>
            {models.map((m) => (
              <option key={m.uuid} value={m.uuid}>
                {m.name}
              </option>
            ))}
          </select>
        </div>

        <div className='field'>
          <label className='field__label' htmlFor='exp-run'>
            Run Name
          </label>
          <input
            id='exp-run'
            className='field__input'
            placeholder='e.g. baseline-v1'
            value={runName}
            onChange={(e) => setRunName(e.target.value)}
          />
        </div>

        <div className='field'>
          <label className='field__label' htmlFor='exp-seed'>
            Seed
          </label>
          <input
            id='exp-seed'
            type='number'
            className='field__input'
            placeholder='42'
            value={seed}
            onChange={(e) => setSeed(e.target.value)}
          />
        </div>

        <div className='field'>
          <label className='field__label' htmlFor='exp-notes'>
            Notes
          </label>
          <textarea
            id='exp-notes'
            className='field__input'
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>

        <div className='form__actions'>
          <button type='submit' className='btn btn--primary' disabled={loading}>
            {loading ? 'Submitting...' : 'Submit Experiment'}
          </button>
          <button type='button' className='btn btn--outline' onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
