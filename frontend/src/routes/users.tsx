import { useState } from 'react'
import { redirect, useLoaderData } from 'react-router'
import UserProfile from '../components/UserProfile'
import { useAuth } from '../contexts/auth'
import { useSnackBar } from '../contexts/snackbar'
import { User } from '../models/user'
import userService from '../services/user.service'

export async function loader() {
  try {
    const users = await userService.getUsers()
    return { users }
  } catch {
    return redirect('/')
  }
}

export default function Users() {
  const { users: initialUsers } = useLoaderData() as { users: User[] }
  const { user: currentUser } = useAuth()
  const { showSnackBar } = useSnackBar()
  const [users, setUsers] = useState<User[]>(initialUsers)
  const [selectedUser, setSelectedUser] = useState<User | undefined>()
  const [toDelete, setToDelete] = useState<User | undefined>()
  const [confirmOpen, setConfirmOpen] = useState(false)

  const handleUserUpdate = (updated: User) => {
    setUsers((prev) => prev.map((u) => (u.uuid === updated.uuid ? updated : u)))
  }

  const handleConfirmDelete = async () => {
    if (!toDelete) return
    setConfirmOpen(false)
    await userService.deleteUser(toDelete.uuid)
    showSnackBar('User deleted successfully.', 'success')
    setUsers((prev) => prev.filter((u) => u.uuid !== toDelete.uuid))
    if (selectedUser?.uuid === toDelete.uuid) setSelectedUser(undefined)
    setToDelete(undefined)
  }

  return (
    <div className='page container'>
      <div className='users-layout'>
        {/* Left: user list */}
        <div className='user-list-panel'>
          <ul className='user-list'>
            {users.map((u) => {
              const initials = u.first_name
                ? u.first_name[0].toUpperCase()
                : u.email[0].toUpperCase()
              const fullName = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.email
              const isSelected = selectedUser?.uuid === u.uuid

              return (
                <li
                  key={u.uuid}
                  className={`user-list__item${isSelected ? ' user-list__item--selected' : ''}`}
                >
                  <button
                    className='user-list__btn'
                    onClick={() => setSelectedUser(u)}
                    aria-current={isSelected ? 'true' : undefined}
                  >
                    <div className='avatar avatar--sm'>
                      {u.picture ? (
                        <img className='avatar__img' src={u.picture} alt={fullName} />
                      ) : (
                        <span>{initials}</span>
                      )}
                    </div>
                    <div className='user-list__info'>
                      <span className='user-list__name'>{fullName}</span>
                      <span className='user-list__email'>{u.email}</span>
                    </div>
                  </button>

                  {/* Delete (only non-self) */}
                  {currentUser?.uuid !== u.uuid && (
                    <button
                      className='btn btn--ghost btn--icon user-list__delete'
                      aria-label={`Delete ${fullName}`}
                      onClick={() => {
                        setToDelete(u)
                        setConfirmOpen(true)
                      }}
                    >
                      <svg
                        viewBox='0 0 24 24'
                        fill='none'
                        stroke='currentColor'
                        strokeWidth='2'
                        width='16'
                        height='16'
                      >
                        <polyline points='3 6 5 6 21 6' />
                        <path d='M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6' />
                        <path d='M10 11v6M14 11v6' />
                        <path d='M9 6V4h6v2' />
                      </svg>
                    </button>
                  )}
                </li>
              )
            })}
          </ul>
        </div>

        {/* Right: user profile editor */}
        <div className='user-detail-panel'>
          {selectedUser ? (
            <UserProfile
              userProfile={selectedUser}
              onUserUpdated={handleUserUpdate}
              allowDelete={currentUser?.uuid === selectedUser.uuid}
            />
          ) : (
            <div className='user-detail-panel__empty'>
              <p className='text-muted'>Select a user to view details.</p>
            </div>
          )}
        </div>
      </div>

      {/* Confirm delete dialog */}
      {confirmOpen && toDelete && (
        <div
          className='dialog-backdrop'
          role='dialog'
          aria-modal='true'
          aria-labelledby='del-dialog-title'
        >
          <div className='dialog'>
            <div className='dialog__header'>
              <h2 className='dialog__title' id='del-dialog-title'>
                Delete user
              </h2>
            </div>
            <div className='dialog__body'>
              Delete{' '}
              <strong>
                {[toDelete.first_name, toDelete.last_name].filter(Boolean).join(' ') ||
                  toDelete.email}
              </strong>
              ? This action cannot be undone.
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
