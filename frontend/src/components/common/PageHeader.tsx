import type { ReactNode } from 'react'

type Props = {
  title: string
  children?: ReactNode
}

export default function PageHeader({ title, children }: Props) {
  return (
    <div className='page-header'>
      <h1 className='page-header__title'>{title}</h1>
      {children && <div className='page-header__actions'>{children}</div>}
    </div>
  )
}
