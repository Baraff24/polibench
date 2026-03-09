import { useEffect } from 'react'
import { useLocation } from 'react-router'

const TITLES: Record<string, string> = {
  '/': 'Home',
  '/login': 'Login',
  '/register': 'Register',
  '/profile': 'Profile',
  '/users': 'Users',
  '/leaderboard': 'Leaderboard',
  '/datasets': 'Datasets',
  '/datasets/new': 'New Dataset',
  '/models': 'Models',
  '/models/new': 'New Model',
  '/experiments/new': 'Submit Experiment',
  '/verify-email': 'Verify Email',
}

export default function useDocumentTitle() {
  const { pathname } = useLocation()

  useEffect(() => {
    const base = 'Polibench'

    // Exact match
    const exact = TITLES[pathname]
    if (exact) {
      document.title = exact + ' — ' + base
      return
    }

    // Dynamic routes
    if (pathname.startsWith('/datasets/')) {
      document.title = 'Dataset — ' + base
      return
    }
    if (pathname.startsWith('/models/')) {
      document.title = 'Model — ' + base
      return
    }
    if (pathname.startsWith('/experiments/')) {
      document.title = 'Experiment — ' + base
      return
    }

    document.title = base
  }, [pathname])
}
