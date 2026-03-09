import { useState, useRef, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router'
import { useAuth } from '../contexts/auth'

type Props = {
  sidebarOpen: boolean
  onToggleSidebar: () => void
}

function navItemClass(isActive: boolean): string {
  if (isActive) return 'sidebar__item sidebar__item--active'
  return 'sidebar__item'
}

export default function TopMenuBar({ sidebarOpen, onToggleSidebar }: Props) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Chiude il dropdown cliccando fuori
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleLogout = () => {
    setMenuOpen(false)
    logout()
    navigate('/')
  }

  const closeSidebarOnMobile = () => {
    if (window.innerWidth < 768) {
      onToggleSidebar()
    }
  }

  let initials = 'P'
  if (user?.first_name) {
    initials = user.first_name[0].toUpperCase()
  }
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ')

  let sidebarClass = 'sidebar'
  if (!sidebarOpen) {
    sidebarClass = 'sidebar sidebar--hidden'
  }
  let topbarClass = 'topbar'
  if (!sidebarOpen) {
    topbarClass = 'topbar topbar--full'
  }
  let dropdownMenuClass = 'dropdown__menu'
  if (menuOpen) {
    dropdownMenuClass = 'dropdown__menu dropdown__menu--open'
  }

  return (
    <>
      {/* Mobile overlay */}
      <div
        className={sidebarOpen ? 'sidebar-overlay sidebar-overlay--visible' : 'sidebar-overlay'}
        onClick={onToggleSidebar}
      />

      {/* Sidebar */}
      <aside className={sidebarClass}>
        <div className='sidebar__brand'>
          <NavLink to='/' className='sidebar__brand-link'>
            <span className='sidebar__brand-name'>Polibench</span>
          </NavLink>
          <button className='sidebar__close' aria-label='Close sidebar' onClick={onToggleSidebar}>
            <svg
              width='18'
              height='18'
              viewBox='0 0 24 24'
              fill='none'
              stroke='currentColor'
              strokeWidth='2'
            >
              <line x1='18' y1='6' x2='6' y2='18' />
              <line x1='6' y1='6' x2='18' y2='18' />
            </svg>
          </button>
        </div>

        <nav className='sidebar__nav'>
          <div className='sidebar__section-label'>Menu</div>

          <NavLink
            to='/'
            end
            className={({ isActive }) => navItemClass(isActive)}
            onClick={closeSidebarOnMobile}
          >
            <svg
              className='sidebar__item-icon'
              viewBox='0 0 24 24'
              fill='none'
              stroke='currentColor'
              strokeWidth='2'
            >
              <path d='M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z' />
              <polyline points='9 22 9 12 15 12 15 22' />
            </svg>
            Home
          </NavLink>

          <NavLink
            to='/leaderboard'
            className={({ isActive }) => navItemClass(isActive)}
            onClick={closeSidebarOnMobile}
          >
            <svg
              className='sidebar__item-icon'
              viewBox='0 0 24 24'
              fill='none'
              stroke='currentColor'
              strokeWidth='2'
            >
              <path d='M18 20V10M12 20V4M6 20v-6' />
            </svg>
            Leaderboard
          </NavLink>

          <NavLink
            to='/datasets'
            className={({ isActive }) => navItemClass(isActive)}
            onClick={closeSidebarOnMobile}
          >
            <svg
              className='sidebar__item-icon'
              viewBox='0 0 24 24'
              fill='none'
              stroke='currentColor'
              strokeWidth='2'
            >
              <ellipse cx='12' cy='5' rx='9' ry='3' />
              <path d='M21 12c0 1.66-4 3-9 3s-9-1.34-9-3' />
              <path d='M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5' />
            </svg>
            Datasets
          </NavLink>

          <NavLink
            to='/models'
            className={({ isActive }) => navItemClass(isActive)}
            onClick={closeSidebarOnMobile}
          >
            <svg
              className='sidebar__item-icon'
              viewBox='0 0 24 24'
              fill='none'
              stroke='currentColor'
              strokeWidth='2'
            >
              <path d='M12 2L2 7l10 5 10-5-10-5z' />
              <path d='M2 17l10 5 10-5' />
              <path d='M2 12l10 5 10-5' />
            </svg>
            Models
          </NavLink>

          {user !== undefined && (
            <NavLink
              to='/experiments/new'
              className={({ isActive }) => navItemClass(isActive)}
              onClick={closeSidebarOnMobile}
            >
              <svg
                className='sidebar__item-icon'
                viewBox='0 0 24 24'
                fill='none'
                stroke='currentColor'
                strokeWidth='2'
              >
                <line x1='12' y1='5' x2='12' y2='19' />
                <line x1='5' y1='12' x2='19' y2='12' />
              </svg>
              Submit Experiment
            </NavLink>
          )}

          {/* Guest */}
          {user === undefined && (
            <>
              <NavLink
                to='/login'
                className={({ isActive }) => navItemClass(isActive)}
                onClick={closeSidebarOnMobile}
              >
                <svg
                  className='sidebar__item-icon'
                  viewBox='0 0 24 24'
                  fill='none'
                  stroke='currentColor'
                  strokeWidth='2'
                >
                  <path d='M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4' />
                  <polyline points='10 17 15 12 10 7' />
                  <line x1='15' y1='12' x2='3' y2='12' />
                </svg>
                Login
              </NavLink>
              <NavLink
                to='/register'
                className={({ isActive }) => navItemClass(isActive)}
                onClick={closeSidebarOnMobile}
              >
                <svg
                  className='sidebar__item-icon'
                  viewBox='0 0 24 24'
                  fill='none'
                  stroke='currentColor'
                  strokeWidth='2'
                >
                  <path d='M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2' />
                  <circle cx='8.5' cy='7' r='4' />
                  <line x1='20' y1='8' x2='20' y2='14' />
                  <line x1='23' y1='11' x2='17' y2='11' />
                </svg>
                Register
              </NavLink>
            </>
          )}

          {/* Admin-only */}
          {user?.is_superuser && (
            <>
              <div className='sidebar__section-label'>Admin</div>
              <NavLink
                to='/users'
                className={({ isActive }) => navItemClass(isActive)}
                onClick={closeSidebarOnMobile}
              >
                <svg
                  className='sidebar__item-icon'
                  viewBox='0 0 24 24'
                  fill='none'
                  stroke='currentColor'
                  strokeWidth='2'
                >
                  <path d='M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2' />
                  <circle cx='9' cy='7' r='4' />
                  <path d='M23 21v-2a4 4 0 00-3-3.87' />
                  <path d='M16 3.13a4 4 0 010 7.75' />
                </svg>
                Users
              </NavLink>
            </>
          )}
        </nav>
      </aside>

      {/* Topbar */}
      <header className={topbarClass}>
        {!sidebarOpen && (
          <button className='topbar__toggle' aria-label='Open sidebar' onClick={onToggleSidebar}>
            <svg
              width='20'
              height='20'
              viewBox='0 0 24 24'
              fill='none'
              stroke='currentColor'
              strokeWidth='2'
            >
              <line x1='3' y1='6' x2='21' y2='6' />
              <line x1='3' y1='12' x2='21' y2='12' />
              <line x1='3' y1='18' x2='21' y2='18' />
            </svg>
          </button>
        )}

        <div className='topbar__right'>
          {user === undefined && (
            <div className='dropdown' ref={dropdownRef}>
              <button
                className='topbar__avatar-btn'
                aria-expanded={menuOpen}
                aria-haspopup='true'
                aria-label='Account menu'
                onClick={() => setMenuOpen((v) => !v)}
              >
                <span className='avatar avatar--sm'>
                  <svg
                    width='16'
                    height='16'
                    viewBox='0 0 24 24'
                    fill='none'
                    stroke='currentColor'
                    strokeWidth='2'
                  >
                    <path d='M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2' />
                    <circle cx='12' cy='7' r='4' />
                  </svg>
                </span>
              </button>

              <div className={dropdownMenuClass}>
                <NavLink to='/login' className='dropdown__item' onClick={() => setMenuOpen(false)}>
                  Login
                </NavLink>
                <NavLink
                  to='/register'
                  className='dropdown__item'
                  onClick={() => setMenuOpen(false)}
                >
                  Register
                </NavLink>
              </div>
            </div>
          )}

          {user !== undefined && (
            <div className='dropdown' ref={dropdownRef}>
              <button
                className='topbar__avatar-btn'
                aria-expanded={menuOpen}
                aria-haspopup='true'
                aria-label='Account menu'
                onClick={() => setMenuOpen((v) => !v)}
              >
                {user.picture && (
                  <img className='avatar avatar--sm' src={user.picture} alt={fullName} />
                )}
                {!user.picture && <span className='avatar avatar--sm'>{initials}</span>}
                <span className='topbar__user-name'>{fullName || 'Account'}</span>
              </button>

              <div className={dropdownMenuClass}>
                <NavLink
                  to='/profile'
                  className='dropdown__item'
                  onClick={() => setMenuOpen(false)}
                >
                  Profile
                </NavLink>
                <div className='dropdown__divider' />
                <button className='dropdown__item dropdown__item--danger' onClick={handleLogout}>
                  Logout
                </button>
              </div>
            </div>
          )}
        </div>
      </header>
    </>
  )
}
