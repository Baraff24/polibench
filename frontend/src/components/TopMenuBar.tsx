import { useState, useRef, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router'
import { useAuth } from '../contexts/auth'

export default function TopMenuBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Chiude il dropdown cliccando fuori
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleLogout = () => {
    setOpen(false)
    logout()
    navigate('/')
  }

  const initials = user?.first_name ? user.first_name[0].toUpperCase() : 'P'
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ')

  return (
    <nav className='navbar' role='navigation' aria-label='Main navigation'>
      <div className='navbar__inner'>
        {/* Brand */}
        <NavLink to='/' className='navbar__brand'>
          Polibench
        </NavLink>

        {/* Nav links + actions */}
        <div className='navbar__nav'>
          {/* Guest */}
          {user === undefined && (
            <>
              <NavLink
                to='/login'
                className={({ isActive }) =>
                  `navbar__link${isActive ? ' navbar__link--active' : ''}`
                }
              >
                Login
              </NavLink>
              <NavLink
                to='/register'
                className={({ isActive }) =>
                  `navbar__link${isActive ? ' navbar__link--active' : ''}`
                }
              >
                Register
              </NavLink>
            </>
          )}

          {/* Admin-only */}
          {user?.is_superuser && (
            <NavLink
              to='/users'
              className={({ isActive }) => `navbar__link${isActive ? ' navbar__link--active' : ''}`}
            >
              Users
            </NavLink>
          )}

          {/* Avatar dropdown */}
          {user !== undefined && (
            <div className='dropdown' ref={dropdownRef}>
              <button
                className='navbar__avatar-btn'
                aria-expanded={open}
                aria-haspopup='true'
                aria-label='Account menu'
                onClick={() => setOpen((v) => !v)}
              >
                {user.picture ? (
                  <img className='navbar__avatar-img' src={user.picture} alt={fullName} />
                ) : (
                  <span className='navbar__avatar-initials' aria-hidden='true'>
                    {initials}
                  </span>
                )}
              </button>

              <div className={`dropdown__menu${open ? ' dropdown__menu--open' : ''}`}>
                <NavLink to='/profile' className='dropdown__item' onClick={() => setOpen(false)}>
                  <svg
                    className='dropdown__icon'
                    viewBox='0 0 24 24'
                    fill='none'
                    stroke='currentColor'
                    strokeWidth='2'
                  >
                    <path d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2' />
                    <circle cx='12' cy='7' r='4' />
                  </svg>
                  Profile
                </NavLink>
                <div className='dropdown__divider' />
                <button className='dropdown__item' onClick={handleLogout}>
                  <svg
                    className='dropdown__icon'
                    viewBox='0 0 24 24'
                    fill='none'
                    stroke='currentColor'
                    strokeWidth='2'
                  >
                    <path d='M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4' />
                    <polyline points='16 17 21 12 16 7' />
                    <line x1='21' y1='12' x2='9' y2='12' />
                  </svg>
                  Logout
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
