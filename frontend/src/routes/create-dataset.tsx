import { useState } from 'react'
import { useNavigate } from 'react-router'
import { PageHeader } from '../components'
import { datasetService } from '../services'
import { useSnackBar } from '../contexts/snackbar'
import type { TaskType, Visibility } from '../models'

export default function CreateDataset() {
  const navigate = useNavigate()
  const { showSnackBar } = useSnackBar()
  const [loading, setLoading] = useState(false)

  const [name, setName] = useState('')
  const [task, setTask] = useState<TaskType>('ranking')
  const [visibility, setVisibility] = useState<Visibility>('public')
  const [description, setDescription] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      showSnackBar('Name is required.', 'error')
      return
    }
    setLoading(true)
    try {
      const dataset = await datasetService.create({
        name: name.trim(),
        task,
        visibility,
        description: description.trim() || undefined,
      })
      showSnackBar('Dataset created. Add the first version with YAML in the detail page.', 'success')
      navigate('/datasets/' + dataset.uuid)
    } catch {
      showSnackBar('Error creating dataset.', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className='page container container--narrow'>
      <PageHeader title='New Dataset' />

      <form className='form' onSubmit={handleSubmit}>
        <div className='field'>
          <label className='field__label' htmlFor='ds-name'>
            Name
          </label>
          <input
            id='ds-name'
            className='field__input'
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>

        <div className='field'>
          <label className='field__label' htmlFor='ds-task'>
            Task
          </label>
          <select
            id='ds-task'
            className='field__input'
            value={task}
            onChange={(e) => setTask(e.target.value as TaskType)}
          >
            <option value='ranking'>Ranking</option>
            <option value='rating_prediction'>Rating Prediction</option>
          </select>
        </div>

        <div className='field'>
          <label className='field__label' htmlFor='ds-visibility'>
            Visibility
          </label>
          <select
            id='ds-visibility'
            className='field__input'
            value={visibility}
            onChange={(e) => setVisibility(e.target.value as Visibility)}
          >
            <option value='public'>Public</option>
            <option value='private'>Private</option>
          </select>
        </div>

        <div className='field'>
          <label className='field__label' htmlFor='ds-desc'>
            Description
          </label>
          <textarea
            id='ds-desc'
            className='field__input'
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div className='form__actions'>
          <button type='submit' className='btn btn--primary' disabled={loading}>
            {loading ? 'Creating...' : 'Create Dataset'}
          </button>
          <button type='button' className='btn btn--outline' onClick={() => navigate('/datasets')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
