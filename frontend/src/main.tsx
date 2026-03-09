import './styles/main.scss'
import './axios'
import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router'
import { router } from './router'
import { SnackBarProvider } from './contexts/snackbar'
import { AuthProvider } from './contexts/auth'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <AuthProvider>
      <SnackBarProvider>
        <RouterProvider router={router} />
      </SnackBarProvider>
    </AuthProvider>
  </React.StrictMode>,
)
