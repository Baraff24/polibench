import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router'
import { PageHeader } from '../components'
import { datasetService, mlModelService, experimentService } from '../services'
import { useSnackBar } from '../contexts/snackbar'
import type { DatasetSummary, MLModelSummary } from '../models'

export default function SubmitExperiment() {
  const navigate = useNavigate()
  const { showSnackBar } = useSnackBar()
  const [loading, setLoading] = useState(false)

  const [datasets, setDatasets] = useState<DatasetSummary[]>([])
  const [models, setModels] = useState<MLModelSummary[]>([])

  const [datasetUuid, setDatasetUuid] = useState('')
  const [modelUuid, setModelUuid] = useState('')
  const [runName, setRunName] = useState('')
  const [seed, setSeed] = useState('')
  const [notes, setNotes] = useState('')

  useEffect(() => {
    datasetService.getAll().then(setDatasets)
    mlModelService.getAll().then(setModels)
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!datasetUuid || !modelUuid) {
      showSnackBar('Please select a dataset and a model.', 'error')
      return
    }
    setLoading(true)
    try {
      const experiment = await experimentService.create({
        dataset_uuid: datasetUuid,
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
                {d.name} v{d.version} ({d.task})
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
