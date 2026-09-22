import type { TextareaHTMLAttributes } from 'react'

import { cn } from '../../lib/utils'

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        'min-h-16 w-full rounded-md border bg-surface px-3 py-2 text-sm text-fg',
        'placeholder:text-muted-fg outline-none transition-colors',
        'focus-visible:border-brand focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    />
  )
}
