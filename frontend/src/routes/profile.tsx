import UserProfile from '../components/UserProfile'
import { useAuth } from '../contexts/auth'

export function Profile() {
  const { user } = useAuth()
  return user ? <UserProfile userProfile={user} allowDelete={true} /> : null
}
