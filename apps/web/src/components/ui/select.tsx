import type { SelectHTMLAttributes } from 'react'

import { cn } from '../../lib/utils'

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        'h-9 rounded-md border bg-surface px-2 text-sm text-fg',
        'outline-none transition-colors',
        'focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    />
  )
}
