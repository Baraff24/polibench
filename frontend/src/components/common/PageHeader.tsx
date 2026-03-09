import type { ReactNode } from 'react'

type Props = {
  title: string
  action?: ReactNode
  children?: ReactNode
}

export default function PageHeader({ title, action, children }: Props) {
  return (
    <div className='page-header'>
      <h1 className='page-header__title'>{title}</h1>
      {action && <div className='page-header__actions'>{action}</div>}
      {children && <div className='page-header__actions'>{children}</div>}
    </div>
  )
}
