import { Navigate } from 'react-router'
import type { ReactNode } from 'react'
import { useAuth } from '../../contexts/auth.tsx'
import LoadingSpinner from './LoadingSpinner.tsx'

type Props = {
  children: ReactNode
  adminOnly?: boolean
}

export default function RequireAuth({ children, adminOnly = false }: Props) {
  const { user, loading } = useAuth()

  if (loading) {
    return <LoadingSpinner />
  }

  if (user === undefined) {
    return <Navigate to='/login' replace />
  }

  if (adminOnly && !user.is_superuser) {
    return <Navigate to='/' replace />
  }

  return <>{children}</>
}
