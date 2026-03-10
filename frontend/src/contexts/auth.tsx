import { createContext, FC, useState, ReactNode, useContext, useEffect } from 'react'
import { userService, authService } from '../services'
import type { User } from '../models'

type AuthContextType = {
  user: User | undefined
  loading: boolean
  setUser: (user: User | undefined) => void
  login: (data: FormData) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType)

interface AuthContextProviderProps {
  children: ReactNode
}

const AuthProvider: FC<AuthContextProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User>()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchUserProfile() {
      // Salta se non c'è token — evita race condition con SSO callback
      if (!localStorage.getItem('token')) {
        setLoading(false)
        return
      }
      try {
        const u = await userService.getProfile()
        setUser(u)
      } catch {
        setUser(undefined)
      } finally {
        setLoading(false)
      }
    }
    fetchUserProfile()
  }, [])

  const login = async (data: FormData) => {
    await authService.login(data)
    const u = await userService.getProfile()
    setUser(u)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(undefined)
  }

  return (
    <AuthContext.Provider value={{ user, loading, setUser, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

const useAuth = (): AuthContextType => {
  return useContext(AuthContext)
}

export { AuthProvider, useAuth }
