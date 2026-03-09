import { useState } from 'react'
import { useNavigate } from 'react-router'
import { PageHeader } from '../components'
import { mlModelService } from '../services'
import { useSnackBar } from '../contexts/snackbar'

export default function CreateModel() {
  const navigate = useNavigate()
  const { showSnackBar } = useSnackBar()
  const [loading, setLoading] = useState(false)

  const [name, setName] = useState('')
  const [family, setFamily] = useState('')
  const [paperUrl, setPaperUrl] = useState('')
  const [implementation, setImplementation] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      showSnackBar('Name is required.', 'error')
      return
    }
    setLoading(true)
    try {
      const model = await mlModelService.create({
        name: name.trim(),
        family: family.trim() || undefined,
        paper_url: paperUrl.trim() || undefined,
        implementation: implementation.trim() || undefined,
      })
      showSnackBar('Model registered!', 'success')
      navigate('/models/' + model.uuid)
    } catch {
      showSnackBar('Error creating model.', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className='page container container--narrow'>
      <PageHeader title='New Model' />

      <form className='form' onSubmit={handleSubmit}>
        <div className='field'>
          <label className='field__label' htmlFor='ml-name'>
            Name
          </label>
          <input
            id='ml-name'
            className='field__input'
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>

        <div className='field'>
          <label className='field__label' htmlFor='ml-family'>
            Family
          </label>
          <input
            id='ml-family'
            className='field__input'
            placeholder='e.g. collaborative-filtering, deep-learning'
            value={family}
            onChange={(e) => setFamily(e.target.value)}
          />
        </div>

        <div className='field'>
          <label className='field__label' htmlFor='ml-paper'>
            Paper URL
          </label>
          <input
            id='ml-paper'
            type='url'
            className='field__input'
            placeholder='https://arxiv.org/abs/...'
            value={paperUrl}
            onChange={(e) => setPaperUrl(e.target.value)}
          />
        </div>

        <div className='field'>
          <label className='field__label' htmlFor='ml-impl'>
            Implementation URL
          </label>
          <input
            id='ml-impl'
            type='url'
            className='field__input'
            placeholder='https://github.com/...'
            value={implementation}
            onChange={(e) => setImplementation(e.target.value)}
          />
        </div>

        <div className='form__actions'>
          <button type='submit' className='btn btn--primary' disabled={loading}>
            {loading ? 'Registering...' : 'Register Model'}
          </button>
          <button type='button' className='btn btn--outline' onClick={() => navigate('/models')}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
