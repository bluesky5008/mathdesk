import type { ReactNode } from 'react'
import { NavLink } from 'react-router'

import { Button } from './ui/button'

const NAV = [
  { to: '/', label: '종합 대시보드' },
  { to: '/daily', label: '일일 수업 & 성적 입력' },
  { to: '/students', label: '학생/반 관리' },
  { to: '/messages', label: '알림문자' },
]

export function AppShell({
  userName,
  userRole,
  onLogout,
  children,
}: {
  userName: string
  userRole: string
  onLogout: () => void
  children: ReactNode
}) {
  return (
    <div className="min-h-screen bg-bg">
      <header className="sticky top-0 z-10 border-b bg-surface">
        <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-8 px-6">
          <span className="text-lg font-semibold tracking-tight text-brand">mathdesk</span>

          <nav className="flex items-center gap-1">
            {NAV.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  [
                    'rounded-md px-3 py-1.5 text-sm transition-colors',
                    'outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring',
                    isActive
                      ? 'bg-accent font-medium text-fg'
                      : 'text-muted-fg hover:bg-accent hover:text-fg',
                  ].join(' ')
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <span className="text-sm text-muted-fg">
              {userName} ({userRole})
            </span>
            <Button type="button" variant="outline" size="sm" onClick={onLogout}>
              로그아웃
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1440px] px-6 py-6">{children}</main>
    </div>
  )
}
