import type { ReactNode } from 'react'

interface StatTileProps {
  label: string
  value: string | number
  sub?: string
  icon?: ReactNode
  variant?: 'default' | 'positive' | 'negative' | 'warning'
}

const iconColor = {
  default:  'text-primary',
  positive: 'text-green-600',
  negative: 'text-red-600',
  warning:  'text-yellow-600',
} as const

export function StatTile({ label, value, sub, icon, variant = 'default' }: Readonly<StatTileProps>) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 flex flex-col gap-1">
      {icon && (
        <div className={`h-4 w-4 ${iconColor[variant]}`}>
          {icon}
        </div>
      )}
      <p className="text-2xl font-bold leading-none">{value}</p>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
    </div>
  )
}
