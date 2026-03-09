type Variant = 'success' | 'error' | 'warning' | 'info' | 'neutral'

type Props = {
  text: string
  variant?: Variant
}

export default function Badge({ text, variant = 'neutral' }: Props) {
  const cls = 'badge badge--' + variant
  return <span className={cls}>{text}</span>
}
