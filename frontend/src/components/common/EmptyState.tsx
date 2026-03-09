type Props = {
  title: string
  description?: string
}

export default function EmptyState({ title, description }: Props) {
  return (
    <div className='empty-state'>
      <p className='empty-state__title'>{title}</p>
      {description && <p className='empty-state__desc'>{description}</p>}
    </div>
  )
}
