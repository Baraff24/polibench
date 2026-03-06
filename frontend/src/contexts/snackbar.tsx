import { createContext, FC, useState, ReactNode, useContext, useCallback } from 'react'

type Severity = 'success' | 'error' | 'warning' | 'info'

type SnackBarContextActions = {
  showSnackBar: (message: string, severity: Severity, timeout?: number) => void
}

const SnackBarContext = createContext<SnackBarContextActions>({} as SnackBarContextActions)

interface Toast {
  id: number
  message: string
  severity: Severity
}

let nextId = 0

const SnackBarProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([])

  const showSnackBar = useCallback((message: string, severity: Severity, timeout = 4000) => {
    const id = ++nextId
    setToasts((prev) => [...prev, { id, message, severity }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, timeout)
  }, [])

  return (
    <SnackBarContext.Provider value={{ showSnackBar }}>
      {children}
      <div className='toast-container' role='region' aria-live='polite'>
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast--${t.severity}`}>
            {t.message}
          </div>
        ))}
      </div>
    </SnackBarContext.Provider>
  )
}

const useSnackBar = (): SnackBarContextActions => {
  const ctx = useContext(SnackBarContext)
  if (!ctx) throw new Error('useSnackBar must be used within a SnackBarProvider')
  return ctx
}

export { SnackBarProvider, useSnackBar }
