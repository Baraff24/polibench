import { useState } from 'react'
import { useParams, useNavigate } from 'react-router'
import { PageHeader } from '../components'
import { experimentService } from '../services'
import { useSnackBar } from '../contexts/snackbar'
import type { Split, Direction, MetricCreate } from '../models'

export default function SubmitMetrics() {
  const { uuid } = useParams<{ uuid: string }>()
  const navigate = useNavigate()
  const { showSnackBar } = useSnackBar()
  const [loading, setLoading] = useState(false)

  const [rows, setRows] = useState<MetricCreate[]>([
    { split: 'test', metric: '', k: null, value: 0, direction: 'max' },
  ])

  const addRow = () => {
    setRows([...rows, { split: 'test', metric: '', k: null, value: 0, direction: 'max' }])
  }

  const removeRow = (idx: number) => {
    setRows(rows.filter((_, i) => i !== idx))
  }

  const updateRow = (idx: number, field: string, val: string | number | null) => {
    const updated = [...rows]
    updated[idx] = { ...updated[idx], [field]: val }
    setRows(updated)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!uuid) return

    const validRows = rows.filter((r) => r.metric.trim() !== '')
    if (validRows.length === 0) {
      showSnackBar('Add at least one metric.', 'error')
      return
    }

    setLoading(true)
    try {
      await experimentService.submitMetrics(uuid, {
        experiment_uuid: uuid,
        metrics: validRows.map((r) => ({
          ...r,
          metric: r.metric.trim(),
        })),
      })
      showSnackBar('Metrics submitted!', 'success')
      navigate('/experiments/' + uuid)
    } catch {
      showSnackBar('Error submitting metrics.', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className='page container'>
      <PageHeader title='Submit Metrics' />
      <p className='text-muted' style={{ marginBottom: '1.5rem' }}>
        Experiment: <code>{uuid}</code>
      </p>

      <form onSubmit={handleSubmit}>
        <div className='table-wrap'>
          <table className='table'>
            <thead>
              <tr>
                <th>Split</th>
                <th>Metric</th>
                <th>k</th>
                <th>Value</th>
                <th>Direction</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={idx}>
                  <td>
                    <select
                      className='field__input'
                      value={row.split}
                      onChange={(e) => updateRow(idx, 'split', e.target.value as Split)}
                    >
                      <option value='test'>test</option>
                      <option value='validation'>validation</option>
                    </select>
                  </td>
                  <td>
                    <input
                      className='field__input'
                      placeholder='ndcg@10'
                      value={row.metric}
                      onChange={(e) => updateRow(idx, 'metric', e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      type='number'
                      className='field__input'
                      placeholder='—'
                      value={row.k ?? ''}
                      onChange={(e) => {
                        const v = e.target.value
                        updateRow(idx, 'k', v ? Number(v) : null)
                      }}
                    />
                  </td>
                  <td>
                    <input
                      type='number'
                      step='any'
                      className='field__input'
                      value={row.value}
                      onChange={(e) => updateRow(idx, 'value', Number(e.target.value))}
                    />
                  </td>
                  <td>
                    <select
                      className='field__input'
                      value={row.direction}
                      onChange={(e) => updateRow(idx, 'direction', e.target.value as Direction)}
                    >
                      <option value='max'>max</option>
                      <option value='min'>min</option>
                    </select>
                  </td>
                  <td>
                    <button
                      type='button'
                      className='btn btn--outline btn--sm'
                      onClick={() => removeRow(idx)}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className='form__actions' style={{ marginTop: '1rem' }}>
          <button type='button' className='btn btn--outline' onClick={addRow}>
            + Add Metric
          </button>
          <button type='submit' className='btn btn--primary' disabled={loading}>
            {loading ? 'Submitting...' : 'Submit Metrics'}
          </button>
        </div>
      </form>
    </div>
  )
}
