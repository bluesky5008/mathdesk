import type { MouseEventHandler, ReactNode } from 'react'
import { Link } from 'react-router'

import { Card } from './card'

/** 대시보드·일일 입력이 함께 쓰는 KPI 타일. `to`를 주면 타일 전체가 그 화면으로 가는 링크가 된다. */
export function Stat({
  title,
  value,
  children,
  to,
  onClick,
}: {
  title: string
  value: ReactNode
  children?: ReactNode
  to?: string
  onClick?: MouseEventHandler<HTMLAnchorElement>
}) {
  const card = (
    <Card className={to ? 'h-full px-4 py-3.5 transition-colors group-hover:border-brand' : 'px-4 py-3.5'}>
      <h3 className="flex justify-between gap-2 text-xs font-medium text-muted-fg">
        {title}
        {to && (
          <span aria-hidden className="group-hover:text-brand">
            →
          </span>
        )}
      </h3>
      <strong className="mt-1.5 block text-2xl leading-tight font-semibold tabular-nums">
        {value}
      </strong>
      {children && <div className="mt-1.5 flex flex-col gap-0.5 text-xs text-muted-fg">{children}</div>}
    </Card>
  )
  if (!to) return card
  return (
    <Link
      to={to}
      onClick={onClick}
      className="group block rounded-lg outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
    >
      {card}
    </Link>
  )
}
