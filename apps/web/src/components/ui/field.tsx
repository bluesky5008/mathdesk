import type { ReactNode } from 'react'

import { cn } from '../../lib/utils'

/**
 * 레이블과 컨트롤을 한 벌로 묶는다.
 * 레이블 텍스트에 장식을 덧붙이지 않는다. 화면 테스트가 레이블로 컨트롤을 찾기 때문이다.
 */
export function Field({
  label,
  htmlFor,
  className,
  children,
}: {
  label: string
  htmlFor: string
  className?: string
  children: ReactNode
}) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label htmlFor={htmlFor} className="text-xs font-medium text-muted-fg">
        {label}
      </label>
      {children}
    </div>
  )
}
