import { AxiosError } from 'axios'
import { SubmitHandler, useForm } from 'react-hook-form'
import { Link as RouterLink, useNavigate } from 'react-router'
import { useAuth } from '../contexts/auth'
import { useSnackBar } from '../contexts/snackbar'
import type { User } from '../models'
import { authService } from '../services'

export default function LoginForm() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<User>()
  const navigate = useNavigate()
  const { showSnackBar } = useSnackBar()
  const { login } = useAuth()

  const onSubmit: SubmitHandler<User> = async (data) => {
    try {
      const formData = new FormData()
      formData.append('username', data.email)
      formData.append('password', data.password as string)
      await login(formData)
      showSnackBar('Login successful.', 'success')
      navigate('/')
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
    }
  }

  const handleGoogleLogin = () => {
    window.location.href = authService.getGoogleLoginUrl()
  }

  let emailClass = 'field__input'
  if (errors.email) {
    emailClass = 'field__input field__input--error'
  }
  let passwordClass = 'field__input'
  if (errors.password) {
    passwordClass = 'field__input field__input--error'
  }

  return (
    <form className='form' onSubmit={handleSubmit(onSubmit)} noValidate>
      <h1 className='form__title'>Sign in</h1>

      <button type='button' className='btn btn--outline btn--full' onClick={handleGoogleLogin}>
        {/* Google SVG */}
        <svg className='btn__icon' viewBox='0 0 48 48'>
          <path
            fill='#FFC107'
            d='M43.6 20.1H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 8 3l5.7-5.7C34 6.1 29.3 4 24 4 12.95 4 4 13 4 24s9 20 20 20 20-9 20-20c0-1.3-.1-2.7-.4-3.9z'
          />
          <path
            fill='#FF3D00'
            d='M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 8 3l5.7-5.7C34 6.1 29.3 4 24 4c-7.7 0-14.4 4.3-17.7 10.7z'
          />
          <path
            fill='#4CAF50'
            d='M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z'
          />
          <path
            fill='#1976D2'
            d='M43.6 20.1H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.7-.4-3.9z'
          />
        </svg>
        Sign in with Google
      </button>

      <div className='form__divider'>or</div>

      <div className='field'>
        <label className='field__label' htmlFor='email'>
          Email address
        </label>
        <input
          id='email'
          type='email'
          autoComplete='email'
          className={emailClass}
          {...register('email', { required: true })}
        />
        {errors.email && <span className='field__error'>Please provide an email address.</span>}
      </div>

      <div className='field'>
        <label className='field__label' htmlFor='password'>
          Password
        </label>
        <input
          id='password'
          type='password'
          autoComplete='current-password'
          className={passwordClass}
          {...register('password', { required: true })}
        />
        {errors.password && <span className='field__error'>Please provide a password.</span>}
      </div>

      <div className='form__actions'>
        <button type='submit' className='btn btn--primary btn--full'>
          Sign In
        </button>
      </div>

      <p className='form__footer'>
        {"Don't have an account yet? "}
        <RouterLink to='/register'>Sign Up</RouterLink>
      </p>
    </form>
  )
}
