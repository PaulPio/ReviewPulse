import { clsx } from 'clsx'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'positive' | 'mixed' | 'negative' | 'outline'
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        {
          'bg-primary/10 text-primary': variant === 'default',
          'bg-[hsl(var(--sentiment-positive))]/10 text-[hsl(var(--sentiment-positive))]': variant === 'positive',
          'bg-[hsl(var(--sentiment-mixed))]/10 text-[hsl(var(--sentiment-mixed))]': variant === 'mixed',
          'bg-[hsl(var(--sentiment-negative))]/10 text-[hsl(var(--sentiment-negative))]': variant === 'negative',
          'border border-border': variant === 'outline',
        },
        className
      )}
      {...props}
    />
  )
}
