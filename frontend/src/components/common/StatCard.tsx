import type { ReactNode } from 'react'

type Props = {
  label: string
  value: string | number
  icon?: ReactNode
}

export default function StatCard({ label, value, icon }: Props) {
  return (
    <div className='stat-card'>
      {icon && <div className='stat-card__icon'>{icon}</div>}
      <div className='stat-card__body'>
        <span className='stat-card__value'>{value}</span>
        <span className='stat-card__label'>{label}</span>
      </div>
    </div>
  )
}
