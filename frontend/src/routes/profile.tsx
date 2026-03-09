import { UserProfile } from '../components'
import { useAuth } from '../contexts/auth'

export function Profile() {
  const { user } = useAuth()

  if (!user) return null

  return <UserProfile userProfile={user} allowDelete={true} />
}
