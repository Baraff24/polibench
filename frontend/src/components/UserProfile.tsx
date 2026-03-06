import { AxiosError } from 'axios'
import { useEffect, useState } from 'react'
import { SubmitHandler, useForm } from 'react-hook-form'
import { useNavigate } from 'react-router'
import { useAuth } from '../contexts/auth'
import { useSnackBar } from '../contexts/snackbar'
import { User } from '../models/user'
import userService from '../services/user.service'

interface UserProfileProps {
  userProfile: User
  onUserUpdated?: (user: User) => void
  allowDelete: boolean
}

export default function UserProfile({ userProfile, onUserUpdated, allowDelete }: UserProfileProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<User>({ defaultValues: userProfile })
  const navigate = useNavigate()
  const { user: currentUser, setUser, logout } = useAuth()
  const { showSnackBar } = useSnackBar()
  const [confirmOpen, setConfirmOpen] = useState(false)

  useEffect(() => {
    reset(userProfile)
  }, [userProfile, reset])

  const onSubmit: SubmitHandler<User> = async (data) => {
    try {
      let updated: User
      if (currentUser?.uuid === userProfile.uuid) {
        updated = await userService.updateProfile(data)
        setUser(updated)
      } else {
        updated = await userService.updateUser(userProfile.uuid, data)
      }
      showSnackBar('Profile updated successfully.', 'success')
      onUserUpdated?.(updated)
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

  const handleConfirmDelete = async () => {
    setConfirmOpen(false)
    await userService.deleteSelf()
    showSnackBar('Account deleted.', 'success')
    logout()
    navigate('/')
  }

  const initials = userProfile.first_name ? userProfile.first_name[0].toUpperCase() : 'P'
  const fullName = [userProfile.first_name, userProfile.last_name].filter(Boolean).join(' ')

  return (
    <div className='profile'>
      {/* Header */}
      <div className='profile__header'>
        <div className='avatar avatar--xl'>
          {userProfile.picture ? (
            <img className='avatar__img' src={userProfile.picture} alt={fullName} />
          ) : (
            <span aria-hidden='true'>{initials}</span>
          )}
        </div>
        {fullName && <p className='profile__name'>{fullName}</p>}
        <p className='profile__email'>{userProfile.email}</p>
      </div>

      {/* Edit section */}
      <section className='profile__section'>
        <h2 className='profile__section-title'>Personal information</h2>
        <form className='form' onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className='field'>
            <label className='field__label' htmlFor='first_name'>
              First name
            </label>
            <input
              id='first_name'
              type='text'
              className='field__input'
              {...register('first_name')}
            />
          </div>

          <div className='field'>
            <label className='field__label' htmlFor='last_name'>
              Last name
            </label>
            <input id='last_name' type='text' className='field__input' {...register('last_name')} />
          </div>

          <div className='field'>
            <label className='field__label' htmlFor='email'>
              Email
            </label>
            <input
              id='email'
              type='email'
              className={`field__input${errors.email ? ' field__input--error' : ''}`}
              {...register('email', { required: true })}
            />
            {errors.email && <span className='field__error'>Email is required.</span>}
          </div>

          <div className='form__actions'>
            <button type='submit' className='btn btn--primary'>
              Save changes
            </button>
          </div>
        </form>
      </section>

      {/* Danger zone */}
      {allowDelete && (
        <div className='profile__danger-zone'>
          <h3 className='profile__danger-title'>Danger zone</h3>
          <p className='profile__danger-desc'>
            Deleting your account is permanent and cannot be undone.
          </p>
          <button
            type='button'
            className='btn btn--danger btn--sm'
            onClick={() => setConfirmOpen(true)}
          >
            Delete my account
          </button>
        </div>
      )}

      {/* Confirm dialog */}
      {confirmOpen && (
        <div
          className='dialog-backdrop'
          role='dialog'
          aria-modal='true'
          aria-labelledby='dialog-title'
        >
          <div className='dialog'>
            <div className='dialog__header'>
              <h2 className='dialog__title' id='dialog-title'>
                Delete account
              </h2>
              <button
                className='dialog__close btn btn--ghost btn--icon'
                onClick={() => setConfirmOpen(false)}
                aria-label='Close'
              >
                <svg
                  viewBox='0 0 24 24'
                  fill='none'
                  stroke='currentColor'
                  strokeWidth='2'
                  width='18'
                  height='18'
                >
                  <line x1='18' y1='6' x2='6' y2='18' />
                  <line x1='6' y1='6' x2='18' y2='18' />
                </svg>
              </button>
            </div>
            <div className='dialog__body'>
              Are you sure you want to permanently delete your account? This action cannot be
              undone.
            </div>
            <div className='dialog__footer'>
              <button className='btn btn--outline' onClick={() => setConfirmOpen(false)}>
                Cancel
              </button>
              <button className='btn btn--danger' onClick={handleConfirmDelete}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
