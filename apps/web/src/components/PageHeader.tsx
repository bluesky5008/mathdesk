import type { ReactNode } from 'react'

/** 화면 제목과 필터를 같은 줄에 둔다. 1280px 이상 데스크톱 전용이다(NFR-14). */
export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="mb-5 flex items-end justify-between gap-6">
      <h2 className="text-xl leading-tight font-semibold">{title}</h2>
      {children && <div className="flex items-end gap-3">{children}</div>}
    </div>
  )
}
