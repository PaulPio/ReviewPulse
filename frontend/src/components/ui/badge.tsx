import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const variants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'border-zinc-600 bg-zinc-800 text-zinc-200',
        positive: 'border-emerald-800 bg-emerald-950/60 text-emerald-200',
        mixed: 'border-amber-800 bg-amber-950/50 text-amber-100',
        negative: 'border-red-800 bg-red-950/50 text-red-200',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

export function Badge({
  className,
  variant,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof variants>) {
  return <div className={cn(variants({ variant, className }))} {...props} />
}
