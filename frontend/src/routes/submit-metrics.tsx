import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { PageHeader } from '../components'
import { experimentService } from '../services'
import { useSnackBar } from '../contexts/snackbar'
import type { MetricImportPublic } from '../models'

export default function SubmitMetrics() {
  const { uuid } = useParams<{ uuid: string }>()
  const navigate = useNavigate()
  const { showSnackBar } = useSnackBar()
  const [loading, setLoading] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [job, setJob] = useState<MetricImportPublic | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!uuid || !file) {
      showSnackBar('Select a CSV file first.', 'error')
      return
    }

    setLoading(true)
    try {
      const createdJob = await experimentService.importMetricsCsv(uuid, file)
      setJob(createdJob)
      showSnackBar('CSV uploaded. Import job queued.', 'success')
    } catch {
      showSnackBar('Error uploading CSV.', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className='page container container--narrow'>
      <PageHeader title='Import Metrics CSV' />
      <p className='text-muted' style={{ marginBottom: '1rem' }}>
        Experiment: <code>{uuid}</code>
      </p>

      <form className='form' onSubmit={handleSubmit}>
        <div className='field'>
          <label className='field__label' htmlFor='metrics-csv'>
            CSV file
          </label>
          <input
            id='metrics-csv'
            type='file'
            accept='.csv,text/csv'
            className='field__input'
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            required
          />
        </div>

        <div className='form__actions'>
          <button type='submit' className='btn btn--primary' disabled={loading}>
            {loading ? 'Uploading...' : 'Upload CSV'}
          </button>
          <button type='button' className='btn btn--outline' onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>

      {job && (
        <section className='detail-section'>
          <h2 className='detail-section__title'>Import job</h2>
          <div className='detail-grid'>
            <div className='detail-field'>
              <div className='detail-field__label'>Status</div>
              <div className='detail-field__value'>{job.status}</div>
            </div>
            <div className='detail-field'>
              <div className='detail-field__label'>File</div>
              <div className='detail-field__value'>{job.csv_filename}</div>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
