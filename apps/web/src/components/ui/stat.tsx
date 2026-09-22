import type { ReactNode } from 'react'

import { Card } from './card'

/** 대시보드·일일 입력이 함께 쓰는 KPI 타일. */
export function Stat({
  title,
  value,
  children,
}: {
  title: string
  value: ReactNode
  children?: ReactNode
}) {
  return (
    <Card className="px-4 py-3.5">
      <h3 className="text-xs font-medium text-muted-fg">{title}</h3>
      <strong className="mt-1.5 block text-2xl leading-tight font-semibold tabular-nums">
        {value}
      </strong>
      {children && <div className="mt-1.5 flex flex-col gap-0.5 text-xs text-muted-fg">{children}</div>}
    </Card>
  )
}
