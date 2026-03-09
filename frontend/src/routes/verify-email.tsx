import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router'
import axios from 'axios'

const API_URL = import.meta.env.VITE_BACKEND_API_URL

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    const token = searchParams.get('token')
    if (!token) {
      setStatus('error')
      setMessage('Token mancante.')
      return
    }

    axios
      .get(API_URL + 'users/verify/' + token)
      .then((res) => {
        setStatus('success')
        setMessage(res.data.message || 'Email verificata con successo!')
      })
      .catch(() => {
        setStatus('error')
        setMessage('Token non valido o scaduto.')
      })
  }, [searchParams])

  return (
    <div className='page container container--narrow'>
      <div className='verify-email'>
        {status === 'loading' && <p className='text-muted'>Verifica in corso...</p>}

        {status === 'success' && (
          <>
            <div className='verify-email__icon verify-email__icon--success'>
              <svg
                width='48'
                height='48'
                viewBox='0 0 24 24'
                fill='none'
                stroke='currentColor'
                strokeWidth='2'
              >
                <path d='M22 11.08V12a10 10 0 11-5.93-9.14' />
                <polyline points='22 4 12 14.01 9 11.01' />
              </svg>
            </div>
            <h1 className='verify-email__title'>Email verificata</h1>
            <p className='verify-email__desc'>{message}</p>
            <button className='btn btn--primary' onClick={() => navigate('/login')}>
              Vai al login
            </button>
          </>
        )}

        {status === 'error' && (
          <>
            <div className='verify-email__icon verify-email__icon--error'>
              <svg
                width='48'
                height='48'
                viewBox='0 0 24 24'
                fill='none'
                stroke='currentColor'
                strokeWidth='2'
              >
                <circle cx='12' cy='12' r='10' />
                <line x1='15' y1='9' x2='9' y2='15' />
                <line x1='9' y1='9' x2='15' y2='15' />
              </svg>
            </div>
            <h1 className='verify-email__title'>Verifica fallita</h1>
            <p className='verify-email__desc'>{message}</p>
            <button className='btn btn--outline' onClick={() => navigate('/register')}>
              Torna alla registrazione
            </button>
          </>
        )}
      </div>
    </div>
  )
}
