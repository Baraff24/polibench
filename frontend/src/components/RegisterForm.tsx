import { AxiosError } from 'axios'
import { SubmitHandler, useForm } from 'react-hook-form'
import { Link as RouterLink, useNavigate } from 'react-router'
import { useSnackBar } from '../contexts/snackbar'
import { User } from '../models/user'
import authService from '../services/auth.service'

const SHOW_EMAIL_REGISTER_FORM: string = import.meta.env.VITE_PWD_SIGNUP_ENABLED

export default function RegisterForm() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<User>()
  const navigate = useNavigate()
  const { showSnackBar } = useSnackBar()

  const onSubmit: SubmitHandler<User> = async (data) => {
    try {
      await authService.register(data)
      showSnackBar('Registration successful.', 'success')
      navigate('/login')
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

  return (
    <div className='form'>
      <h1 className='form__title'>Create account</h1>
      <p className='form__subtitle'>
        No need to sign up — connect with Google and we'll import your profile.
      </p>

      <button type='button' className='btn btn--outline btn--full' onClick={handleGoogleLogin}>
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
        Connect with Google
      </button>

      {SHOW_EMAIL_REGISTER_FORM === 'true' && (
        <>
          <div className='form__divider'>or</div>

          <form onSubmit={handleSubmit(onSubmit)} noValidate className='form'>
            <div className='field'>
              <label className='field__label' htmlFor='first_name'>
                First name
              </label>
              <input
                id='first_name'
                type='text'
                className={`field__input${errors.first_name ? ' field__input--error' : ''}`}
                {...register('first_name', { required: true })}
              />
              {errors.first_name && <span className='field__error'>First name is required.</span>}
            </div>

            <div className='field'>
              <label className='field__label' htmlFor='last_name'>
                Last name
              </label>
              <input
                id='last_name'
                type='text'
                className={`field__input${errors.last_name ? ' field__input--error' : ''}`}
                {...register('last_name', { required: true })}
              />
              {errors.last_name && <span className='field__error'>Last name is required.</span>}
            </div>

            <div className='field'>
              <label className='field__label' htmlFor='email'>
                Email address
              </label>
              <input
                id='email'
                type='email'
                autoComplete='email'
                className={`field__input${errors.email ? ' field__input--error' : ''}`}
                {...register('email', { required: true })}
              />
              {errors.email && (
                <span className='field__error'>Please provide an email address.</span>
              )}
            </div>

            <div className='field'>
              <label className='field__label' htmlFor='password'>
                Password
              </label>
              <input
                id='password'
                type='password'
                className={`field__input${errors.password ? ' field__input--error' : ''}`}
                {...register('password', { required: true })}
              />
              {errors.password && <span className='field__error'>Please provide a password.</span>}
            </div>

            <div className='form__actions'>
              <button type='submit' className='btn btn--primary btn--full'>
                Create account
              </button>
            </div>
          </form>
        </>
      )}

      <p className='form__footer'>
        Already have an account? <RouterLink to='/login'>Sign in</RouterLink>
      </p>
    </div>
  )
}
