import { useEffect } from 'react'
import { redirect, useNavigate } from 'react-router'
import { AxiosError } from 'axios'
import { authService, userService } from '../services'
import { useSnackBar } from '../contexts/snackbar'
import { useAuth } from '../contexts/auth'

export async function loader() {
  try {
    // Scambia il cookie temporaneo con un token JWT persistente in localStorage
    await authService.refreshToken()
    return null
  } catch {
    return redirect('/')
  }
}

export default function SSOLogin() {
  const navigate = useNavigate()
  const { showSnackBar } = useSnackBar()
  const { setUser } = useAuth()

  useEffect(() => {
    async function completeLogin() {
      try {
        // Il token è già in localStorage (salvato dal loader via refreshToken)
        // Basta caricare il profilo utente
        const user = await userService.getProfile()
        setUser(user)
        showSnackBar('Login effettuato con successo.', 'success')
      } catch (error) {
        let msg
        if (
          error instanceof AxiosError &&
          error.response &&
          typeof error.response.data.detail === 'string'
        )
          msg = error.response.data.detail
        else if (error instanceof Error) msg = error.message
        else msg = String(error)
        showSnackBar(msg, 'error')
        setUser(undefined)
      } finally {
        navigate('/')
      }
    }
    completeLogin()
  }, []) // esegue solo al mount

  return (
    <div className='auth'>
      <div className='auth__card'>
        <p className='text-muted text-center'>Completamento login in corso…</p>
      </div>
    </div>
  )
}
