import { isRouteErrorResponse, Link as RouterLink, useRouteError } from 'react-router'

interface RouteError {
  status: number
  statusText: string
  data: string
  message: string
}

export default function ErrorPage() {
  const error = useRouteError() as RouteError

  let status: number | null = null
  if (isRouteErrorResponse(error)) {
    status = error.status
  }

  let title = 'Unexpected error'
  if (status === 404) {
    title = 'Page not found'
  }

  let message = 'Something went wrong.'
  if (isRouteErrorResponse(error)) {
    message = error.statusText || error.data
  } else if ((error as { message?: string })?.message) {
    message = (error as { message: string }).message
  }

  return (
    <div className='auth'>
      <div className='auth__card' style={{ textAlign: 'center' }}>
        {status && (
          <p
            className='text-3xl'
            style={{
              fontWeight: 700,
              color: 'var(--color-primary, #455a64)',
              marginBottom: '0.5rem',
            }}
          >
            {status}
          </p>
        )}
        <h1 className='form__title'>{title}</h1>
        <p className='text-sm text-muted' style={{ marginBottom: '1.5rem' }}>
          {message}
        </p>
        <RouterLink to='/' className='btn btn--primary'>
          Back to home
        </RouterLink>
      </div>
    </div>
  )
}
